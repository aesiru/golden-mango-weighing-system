# CLAUDE.md — Golden Mango Weighing System

## Changes Made (2026-07-31)

### 1. Project Initialization

**docker-compose.yml** — Added PostgreSQL 16 + Mosquitto MQTT broker for local dev:
- `mango-postgres` — PostgreSQL on `:5432`, db `golden_mango_db`, user `mango_user` / `mango_password`
- `mango-mosquitto` — Eclipse Mosquitto 2 on `:1883` (MQTT) + `:9001` (WebSocket), anonymous auth

**mosquitto.conf** — Allows anonymous connections on all interfaces (dev only).

**backend/.env** — Created with DATABASE_URL, SECRET_KEY, CORS, MQTT config.

**frontend/.env** — Created with API + WebSocket URLs pointing to `localhost:8000`.

**backend/uploads/** — Created directory (in .gitignore).

### 2. MQTT Pub/Sub Weight Reader

**New files:**
- `backend/app/infrastructure/mqtt/__init__.py` — Package marker
- `backend/app/infrastructure/mqtt/mqtt_client.py` — `MqttWeightSubscriber` class

**Modified files:**
- `backend/requirements.txt` — Added `aiomqtt` + `paho-mqtt`
- `backend/app/core/config.py` — Added `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_BROKER_USERNAME`, `MQTT_BROKER_PASSWORD`
- `backend/app/main.py` — Start/stop `MqttWeightSubscriber` in lifespan

**Architecture:**
```
ESP32 publishes "385" to "ESP32_01/weight"
  → MqttWeightSubscriber (background asyncio task, subscribes to "#")
  → Filters for "*/weight" topics
  → Matches CrateClass by weight range (narrowest range wins)
  → Finds or creates Order for that class (status: pending/in-progress)
  → Finds or creates Crate for that order (target=50, reuses if not full)
  → Validates weight → Reading.valid = True/False
  → Creates Reading record
  → Updates crate.counted += 1, order.current_amount += weight
  → Emits Socket.IO entity:change events (reading, crate, order)
  → Publishes "{CrateClass_name}: {OrderId}/{CrateId}" to "{device_id}/data"
```

**Edge cases handled:**
- No matching CrateClass → `"Unknown: no class for Xg"`
- No active Order → auto-creates one
- All crates full → auto-creates new crate
- Invalid payload → `"Error: invalid weight '...'"`
- MQTT broker unreachable → retries every 5s with backoff

### 3. Warehouse Seed Data

**New file:** `backend/app/core/seeds/warehouse.py`

**Modified:** `backend/app/core/seeds/__init__.py` — Added warehouse seeds to pipeline

**Seed data:**

| Entity | Data |
|--------|------|
| Company | Mango Export Co. — buyer@mango-export.com, Davao City, approved |
| CrateClass | Small (150-250g), Medium (250-350g), Large (350-500g), Jumbo (500-800g) |
| Order | 1000 Medium mangoes → Mango Export Co., pending |

Run with: `python scripts/setup_system.py --seed-only`

### 4. Bug Fixes

**`backend/scripts/setup_system.py`** — Added missing `await db.commit()` in `step_seed()`. Previously, seeds run via `--seed-only` would flush but never commit (the `--all` flow worked because the subsequent admin creation committed the transaction).

### 5. Admin Credentials

- Username: `admin`
- Password: `admin123`
- Email: `admin@mango.local`

---

## How to Run

```bash
# Start infrastructure
docker compose up -d

# Run seeds (first time)
cd backend
.\.venv\Scripts\activate
python scripts/setup_system.py --seed-only

# Start backend
uvicorn app.main:app --reload --port 8000

# Start frontend (separate terminal)
cd frontend
pnpm dev
```

- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

## How to Test MQTT

```bash
# Publish a weight reading
docker exec mango-mosquitto mosquitto_pub -t "ESP32_01/weight" -m "280"

# Listen for the response
docker exec mango-mosquitto mosquitto_sub -t "ESP32_01/data"
# Output: Medium: ORD-5277ABE4/CRT-F3449E2D
```

---

## Domain Model

```
Company (buyer)
  └── Order (business document: "1000 Medium mangoes")
        └── Crate (physical box: target=50, counted=N)
              └── Reading (single mango: 280g, valid=true)
```

- **device_id** — Opaque ESP32 identifier. No relation to any entity. Used only for MQTT topic routing.
- **Weight → CrateClass** — Matched by `min_weight <= weight <= max_weight`. Narrowest range wins.
- **Weight → Order** — Oldest pending/in-progress order for the matched CrateClass.
- **Weight → Crate** — First crate with spare capacity (`counted < target`) under that order.
