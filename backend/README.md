# Golden Mango Weighing System — Backend

Express.js MVC backend for the IoT mango weighing system.

## Prerequisites

- Node.js 18+
- (Optional) Mosquitto MQTT broker — for weight ingestion

## Setup

```bash
cd backend
npm install
npx prisma db push    # Creates SQLite database
npx prisma db seed     # Seeds admin user and sample data
```

## Run

```bash
npm run dev            # Start on http://localhost:3000
```

## Default Admin

- Username: `admin`
- Password: `admin123`

## API Endpoints

### Auth (public)
| Method | Route | Description |
|---|---|---|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Current user info (auth required) |

### Domain entities (auth required)
| Entity | Base route |
|---|---|
| Companies | `/api/companies` |
| Crate Classes | `/api/crate-classes` |
| Orders | `/api/orders` |
| Crates | `/api/crates` |
| Readings | `/api/readings` (read-only) |

### Admin (superuser required)
| Entity | Base route |
|---|---|
| Users | `/api/users` |
| Roles | `/api/roles` |

All list endpoints support `?page=` and `?pageSize=` pagination. Orders support `PATCH /api/orders/:id/status` for the state machine (pending → in-progress → completed → shipped).

## MQTT

The service listens on `MQTT_TOPIC` (default `+/value`) for weight readings and processes them through the pipeline: match CrateClass → find/create Order → find/create Crate → create Reading → respond on `{device}/display`.

### Test with mosquitto

```bash
# Publish a weight reading (280g = Medium mango)
mosquitto_pub -t "weight/value" -m "280"

# Listen for the LCD response
mosquitto_sub -t "weight/display"
# Expected: Medium: ORD-8F3A2B1C/CRT-1A2B3C4D

# Out-of-range weight
mosquitto_pub -t "weight/value" -m "50"
# Expected: Unknown: no class for 50g
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| DATABASE_URL | `file:./dev.db` | SQLite path or Postgres URL |
| JWT_SECRET | `change-me-in-production` | JWT signing secret |
| JWT_EXPIRES_IN | `12h` | Token expiry |
| PORT | `3000` | HTTP port |
| MQTT_URL | `mqtt://localhost:1883` | MQTT broker |
| MQTT_TOPIC | `+/value` | MQTT topic pattern |

## Switching to PostgreSQL

Change `DATABASE_URL` in `.env` to your Postgres connection string and update `prisma/schema.prisma`:
```diff
- provider = "sqlite"
+ provider = "postgresql"
```
Then run `npx prisma db push` again.
