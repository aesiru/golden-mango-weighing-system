# CLAUDE.md — Hackathon: IoT Mango Weighing System

Two-part project for a hackathon demo: an ESP32-C5 scale with LCD display, and an Express.js backend that stores readings and classifies mangoes by weight.

## Project Layout

```
hackathon/
├── CLAUDE.md                    # This file
├── firmware/                    # ESP32-C5 Arduino sketch
│   └── Hackathon/
│       ├── Hackathon.ino        # Main sketch — LCD, MQTT, buttons
│       └── README.md            # Pin wiring, gotchas
└── backend/                     # Express.js backend (see backend/CLAUDE.md)
    ├── CLAUDE.md                # Detailed backend documentation
    ├── prisma/schema.prisma     # DB schema — 7 tables
    ├── prisma/seed.ts           # Idempotent seed data
    └── src/                     # MVC: models, controllers, routes, services
```

## Data Flow

```
┌──────────────┐     MQTT      ┌─────────────────┐    HTTP/Prisma    ┌──────────┐
│  ESP32-C5    │ ────────────► │  Express.js      │ ───────────────► │  SQLite  │
│  firmware/   │ weight/value  │  backend/        │                  │  (or PG) │
│              │               │                  │                  │          │
│  LCD 16×2    │ ◄──────────── │  MqttService     │                  │          │
│              │ weight/display│  (classify+store)│                  │          │
└──────────────┘               └─────────────────┘                  └──────────┘
```

1. ESP32 publishes a weight (e.g. `"280"`) to `weight/value`
2. Backend receives it, classifies it as "Medium" (250–350g range), finds or creates an Order and Crate, stores a Reading, increments counts
3. Backend responds on `weight/display` with `"Medium: ORD-8F3A2B1C/CRT-1A2B3C4D"`
4. ESP32 LCD displays the response string

## Firmware (`firmware/Hackathon/Hackathon.ino`)

ESP32-C5 Arduino sketch. Key details:

- **Hardware**: ESP32-C5-DevKitC-1, I2C LCD 16×2 (address 0x27 or 0x3F), two buttons
- **Button 1** (GPIO 0): Publishes current weight to `weight/value`
- **Button 2** (GPIO 4): Switches display back to weight value (from MQTT override)
- **WiFi**: Hardcoded in macros — `Cubeworks` / `ProudBisaya`
- **MQTT broker**: `10.40.71.67:1883`
- **Topic contract**: Publish `weight/value`, subscribe `weight/display`
- **Weight source**: Currently a fake counter (`getWeight()`). Replace with real scale sensor.
- **I2C gotcha**: LP_I2C on C5 may need explicit 100 kHz clock. See `firmware/Hackathon/README.md`.

## Backend (`backend/`)

Express.js 5 + TypeScript + Prisma. Full details in `backend/CLAUDE.md`.

**Quick start**:
```bash
cd backend
npm install
npx prisma db push
npx prisma db seed
npm run dev          # → http://localhost:3000
```

**Default admin**: `admin` / `admin123`

**API summary**:
- `POST /api/auth/login` — `{ login, password }` → `{ token, user }`
- `GET /api/companies` — CRUD for companies
- `GET /api/crate-classes` — Weight classes (Small/Medium/Large/Jumbo)
- `GET /api/orders` — Purchase orders with status state machine
- `GET /api/crates` — Physical crates (target=50 mangoes each)
- `GET /api/readings` — Individual weight readings (read-only via HTTP, written via MQTT)
- `GET /api/users`, `GET /api/roles` — Superuser-only admin

**Domain model**:
```
Company → Order → Crate → Reading
              ↘         ↗
             CrateClass (weight grade)
```

**MQTT pipeline** (`backend/src/services/mqtt.service.ts`):
1. Parse weight → NaN? publish error
2. Match CrateClass → no match? publish "Unknown"
3. Find/create Order (oldest pending/in-progress for that class)
4. Find/create Crate (first with `counted < target`)
5. Create Reading, update counts (all in one transaction)
6. Publish `"{ClassName}: {OrderId}/{CrateId}"` to `{device}/display`

## Reference Implementation

`../golden-mango-weighing-system/` — Production-grade version of the same domain in Python/FastAPI/Nuxt. This Express.js backend ports the same 5 domain entities (Company, CrateClass, Order, Crate, Reading) plus User/Role for auth. The reference project also has a full Nuxt frontend, workflow engine, attachment system, and metadata-driven entity system — none of which are ported here (hackathon scope).

**Differences from the reference**:
- MQTT topics: `weight/value` / `weight/display` (firmware contract) vs `{device_id}/weight` / `{device_id}/data` (reference)
- No Socket.IO, no realtime events (simpler)
- No workflow engine, no metadata layer, no attachment system
- SQLite instead of PostgreSQL (switchable)
- Express.js MVC instead of FastAPI Clean Architecture
