# CLAUDE.md — Golden Mango Weighing System (Express.js Backend)

## Project Overview

Express.js + TypeScript backend for an IoT mango weighing system. An ESP32-C5 posts weight readings over MQTT; this backend receives them, classifies each mango by weight grade, associates it with an order and crate, and responds with a short string for a 16×2 LCD display.

Sibling project: `firmware/Hackathon/Hackathon.ino` — the ESP32 firmware that publishes MQTT readings.

Reference implementation (Python): `../golden-mango-weighing-system/` — same domain, same entities, FastAPI + SQLAlchemy.

## Architecture

```
firmware/ESP32                this backend                   database
    │                             │                              │
    ├─ publish "280" ────────────► MqttService ──── Reading ────┤
    │  on weight/value             │ (classify, match,            │
    │                              │  find/create order/crate)    │
    │                              │                              │
    ◄── publish "Medium: ORD/CRT" ─┘                              │
       on weight/display
```

**Stack**: Express.js 5, TypeScript, Prisma ORM, SQLite (dev), Zod validation, JWT auth (jsonwebtoken + bcryptjs), mqtt.js

**Key design decisions**:
- **SQLite by default** — zero infrastructure. Switch to PostgreSQL by changing `provider` in `prisma/schema.prisma` and updating `DATABASE_URL`.
- **No Prisma enums** — SQLite doesn't support them. Status fields are `String` columns with TypeScript union types.
- **Short string IDs** — Every entity gets a readable ID like `ORD-8F3A2B1C` (prefix + 8 hex chars from crypto). This is important because the MQTT response is displayed on a 16-char LCD.
- **No refresh tokens / sessions** — Plain JWT with 12h expiry. Simple, sufficient for hackathon use.
- **No service/repository layers** — Controllers call Prisma directly through a thin model layer. The generic CRUD factory eliminates boilerplate.

## Directory Structure

```
backend/
├── prisma/
│   ├── schema.prisma       # 7 models — the single source of truth for the DB schema
│   └── seed.ts             # Idempotent seed: admin, 4 CrateClasses, 1 Company, 1 Order
├── src/
│   ├── server.ts           # Bootstrap — starts HTTP server, then MQTT, handles SIGINT/SIGTERM
│   ├── app.ts              # Express app — cors, json parsing, /api/health, routes, error handlers
│   ├── config/
│   │   └── env.ts          # Typed env config via dotenv — single import point for all config
│   ├── lib/
│   │   ├── prisma.ts       # PrismaClient singleton (import this, never new PrismaClient())
│   │   ├── ids.ts          # shortId(prefix) → "ORD-A1B2C3D4"
│   │   └── errors.ts       # HttpError class + asyncHandler wrapper for Express routes
│   ├── models/             # Thin wrappers over Prisma — business rules, not raw DB access
│   │   ├── user.model.ts   # sanitize() — strips hashed_password from user objects
│   │   └── order.model.ts  # updateStatus() — state machine enforcing valid transitions
│   ├── controllers/
│   │   ├── crud.controller.ts  # Generic CRUD factory — the heart of the MVC pattern
│   │   ├── auth.controller.ts  # Hand-written: register, login, me
│   │   └── *.controller.ts     # Per-entity — each ~5 lines, instantiates the factory
│   ├── routes/
│   │   ├── index.ts            # Mounts all sub-routers under /api
│   │   └── *.routes.ts         # Per-entity routers — wire middleware + controller methods
│   ├── middlewares/
│   │   ├── auth.ts             # requireAuth (JWT verify + user load), requireSuperuser
│   │   ├── validate.ts         # validate(schema) — zod middleware, 400 on failure
│   │   └── errorHandler.ts     # notFound (404) + errorHandler (HttpError, Prisma P2002/P2025, 500)
│   ├── schemas/                # Zod schemas for request body/query validation
│   └── services/
│       └── mqtt.service.ts     # MqttService — connect, subscribe, pipeline, respond
```

## Domain Model

```
Company (buyer: "Mango Export Co.")
  └── Order ("1000 Medium mangoes", tracked in grams)
        └── Crate (physical box, target=50 mangoes, counted=0..50)
              └── Reading (single mango: weight_grams=280, valid=true/false)
```

**CrateClass** is a standalone classifier referenced by both Order and Crate:
- Small 150–250g, Medium 250–350g, Large 350–500g, Jumbo 500–800g
- Matching: `min_weight <= weight <= max_weight`, narrowest range wins when overlaps exist
- `Reading.valid` is set based on whether the weight falls within its matched class range

## CRUD Controller Factory

The most important architectural pattern. `createCrudController(modelName, options)` returns `{ list, get, create, update, remove }` — standard Express handlers.

```ts
// Example: company.controller.ts
export const companyController = createCrudController('company', {
  idPrefix: 'COMP',
  searchFields: ['name', 'contact_person', 'email', 'phone', 'address', 'status'],
});
```

**Options:**

| Key | Type | Purpose |
|---|---|---|
| `idPrefix` | `string` | Auto-generates IDs on create (e.g. `COMP-8F3A2B1C`) |
| `searchFields` | `string[]` | Pass-through to Prisma (not used for filtering currently — for documentation) |
| `include` | `object` | Prisma include for relations (e.g. `{ company: true, crate_class: true }`) |
| `filters` | `(query) => where` | Maps query string params to Prisma `where` clause |
| `onBeforeDelete` | `async (id) => void` | Guard — throw HttpError to block deletion |
| `onCreateTransform` | `async (data) => data` | Transform body before create (e.g. hash password) |
| `onUpdateTransform` | `async (data) => data` | Transform body before update |
| `sanitize` | `(record) => record` | Strip sensitive fields from output |
| `allowCreate/Update/Delete` | `boolean` | Set to false for read-only entities (e.g. readings) |

**Pagination**: All list endpoints accept `?page=1&pageSize=20` (max 100). Response: `{ data, total, page, pageSize }`.

**Schema is not enforced by the factory** — routes apply zod schemas via the `validate()` middleware before the handler runs.

## MQTT Pipeline

`src/services/mqtt.service.ts` — `MqttService` class, singleton instance exported as `mqttService`.

**Lifecycle**: Created/started in `server.ts` after HTTP listen. Stopped on SIGINT/SIGTERM.

**Serialization**: Messages are processed sequentially via a promise queue (`this.queue = this.queue.then(...)`) to prevent race conditions on `crate.counted` increments.

**Pipeline** (per message):

1. Parse payload → `Number(payload)`. NaN → publish `"Error: invalid weight '...'"`.
2. Match CrateClass: find all where `min_weight <= w <= max_weight`, pick narrowest range.
3. Find or create Order: oldest pending/in-progress for that class. If none, create new with `status: 'in-progress'`.
4. Find or create Crate: first crate under that order with `counted < target`. If all full, create new (`target: 50`).
5. Create Reading with `valid = weight in class range`.
6. `crate.counted += 1`, `order.current_amount += weight` — all in one `prisma.$transaction`.
7. Respond: publish `"{ClassName}: {OrderId}/{CrateId}"` to `{deviceId}/display`.

**Topic contract** (matches the ESP32 firmware):
- Subscribe: `+/value` (configurable via `MQTT_TOPIC`, default `+/value`)
- Publish response: `{deviceId}/display` — device ID is the first segment of the incoming topic
- ESP32 firmware: publishes on `weight/value`, subscribes to `weight/display`

**Edge cases**:
- No matching CrateClass → `"Unknown: no class for Xg"`
- All crates full → auto-creates new crate
- Invalid payload → `"Error: invalid weight '...'"`
- MQTT broker down → mqtt.js auto-reconnects

## Authentication & Authorization

- **JWT payload**: `{ sub: userId, username, is_superuser }`, 12h expiry
- **Login**: Accepts username OR email as `login` field
- **`requireAuth`**: Middleware. Verifies token, loads fresh user from DB (checks `is_active`), attaches `req.user`
- **`requireSuperuser`**: Middleware. Must follow `requireAuth`. 403 if `!user.is_superuser`
- **User output**: Always sanitized via `userModel.sanitize()` — `hashed_password` is never returned

**Auth routes**: `/api/auth/register` (public), `/api/auth/login` (public), `/api/auth/me` (auth required)

**Protected routes**: All domain CRUD endpoints require `requireAuth`. `/api/users` and `/api/roles` additionally require `requireSuperuser`.

## API Routes

| Method | Route | Auth | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | — | Create user, return JWT |
| POST | `/api/auth/login` | — | `{ login, password }` → `{ token, user }` |
| GET | `/api/auth/me` | requireAuth | Current user + roles |
| GET/POST | `/api/companies` | requireAuth | List + create |
| GET/PATCH/DELETE | `/api/companies/:id` | requireAuth | Get, update, delete |
| GET/POST | `/api/crate-classes` | requireAuth | |
| GET/PATCH/DELETE | `/api/crate-classes/:id` | requireAuth | |
| GET/POST | `/api/orders` | requireAuth | List filters: `?company_id=&status=&crate_class_id=` |
| GET/PATCH/DELETE | `/api/orders/:id` | requireAuth | |
| PATCH | `/api/orders/:id/status` | requireAuth | State machine: `pending→in-progress→completed→shipped` |
| GET/POST | `/api/crates` | requireAuth | List filter: `?order_id=` |
| GET/PATCH/DELETE | `/api/crates/:id` | requireAuth | Delete blocked if readings exist |
| GET | `/api/readings` | requireAuth | Read-only. Filters: `?crate_id=&order_id=&from=&to=` |
| GET | `/api/readings/:id` | requireAuth | |
| GET/POST | `/api/users` | requireSuperuser | Password hashed on create/update |
| GET/PATCH/DELETE | `/api/users/:id` | requireSuperuser | |
| GET/POST | `/api/roles` | requireSuperuser | |
| GET/PATCH/DELETE | `/api/roles/:id` | requireSuperuser | |

## Error Handling

Centralized in `src/middlewares/errorHandler.ts`:

| Condition | Status | Response |
|---|---|---|
| `throw new HttpError(status, msg)` | status | `{ message: msg }` |
| Prisma P2002 (unique violation) | 409 | `{ message: "Duplicate value for field" }` |
| Prisma P2025 (record not found) | 404 | `{ message: "Record not found" }` |
| Zod validation failure | 400 | `{ message: "Validation failed", errors: [...] }` |
| Unmatched route | 404 | `{ message: "Not found: METHOD /path" }` |
| Anything else | 500 | `{ message: "Internal server error" }` + console.error |

## Seed Data

`prisma/seed.ts` — idempotent (uses upsert). Run via `npx prisma db seed`.

| Entity | Data |
|---|---|
| User | `admin` / `admin123`, `admin@mango.local`, superuser |
| CrateClass | Small (150–250g), Medium (250–350g), Large (350–500g), Jumbo (500–800g) |
| Company | "Mango Export Co.", info@mangoexport.co, approved |
| Order | 1000 Medium mangoes → Mango Export Co., status: pending |

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `file:./dev.db` | SQLite path or PostgreSQL connection string |
| `JWT_SECRET` | `change-me-in-production` | JWT signing key |
| `JWT_EXPIRES_IN` | `12h` | Token lifetime |
| `PORT` | `3000` | HTTP listen port |
| `MQTT_URL` | `mqtt://localhost:1883` | MQTT broker address |
| `MQTT_TOPIC` | `+/value` | MQTT subscription pattern |

## How to Run

```bash
cd backend
npm install
npx prisma db push       # Create database from schema
npx prisma db seed        # Idempotent seed data
npm run dev               # Start on http://localhost:3000 (tsx watch)
```

Other commands:
```bash
npm run typecheck         # tsc --noEmit
npm run build             # tsc → dist/
npm run start             # node dist/server.js
npx prisma studio         # Visual DB browser
```

## How to Test MQTT

Requires a Mosquitto broker on localhost:1883 (e.g. `docker compose up -d` from the reference project, or `mosquitto -d`).

```bash
# In terminal 1: start the server
cd backend && npm run dev

# In terminal 2: publish a reading
mosquitto_pub -t "weight/value" -m "280"

# Listen for the LCD response
mosquitto_sub -t "weight/display"
# Expected: Medium: ORD-8F3A2B1C/CRT-1A2B3C4D

# In terminal 3: verify via HTTP
TOKEN=$(curl -s -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s http://localhost:3000/api/readings -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

## Key Gotchas & Conventions

- **`asyncHandler` must wrap every async route** — Express 5 doesn't catch promise rejections automatically. Without it, unhandled rejections crash the process.
- **`req.params.id` is `string | string[]`** in Express 5 types — always cast with `as string`.
- **JWT `expiresIn` typing** — `@types/jsonwebtoken` expects a template literal type for `expiresIn`. Cast with `as any` when passing a string from env.
- **Prisma interactive transactions** — `prisma.$transaction(async (tx) => {...})` is used by the MQTT pipeline to ensure atomicity across Reading creation + Crate/Order count increments.
- **Firmware topic contract** differs from the Python reference — the ESP32 uses `weight/value` and `weight/display` (not `{device_id}/weight` and `{device_id}/data`). Configure via `MQTT_TOPIC`.
- **The `prisma` singleton** in `src/lib/prisma.ts` is the only way to get a Prisma client. Never instantiate a new one.
- **No migration files** — using `prisma db push` (prototype mode). For production, switch to `prisma migrate dev`.
- **User password field** is `hashed_password` (matching the Python reference) — never `password` or `password_hash`.
- **Health check** at `GET /api/health` returns `{ status: "ok" }` — useful for monitoring.
