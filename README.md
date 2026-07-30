# 🥭 ManGO — Golden Mango Weighing System

A real-time hardware-integrated weighing and grading management platform for mango exporters. Physical ESP32 scales on the packing floor publish weight readings via MQTT. The system classifies each reading against configurable weight ranges, routes it to the correct crate and company order, and surfaces everything in live dashboards — giving exporters irrefutable proof-of-weight for every shipment.

> _Proof in every reading. Every mango, accounted for._

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Quick Start](#quick-start)
5. [Navigating the Application](#navigating-the-application)
6. [User Roles](#user-roles)
7. [Data Model](#data-model)
8. [Hardware Integration (ESP32 / MQTT)](#hardware-integration-esp32--mqtt)
9. [API Reference](#api-reference)
10. [Git Setup Guide](#git-setup-guide)


---

## Overview

### The Problem
Mango exporters face disputes where buyers claim underweight shipments — but without per-mango records, the exporter has no proof to push back.

### The Solution
Every mango that lands on the scale gets recorded: timestamp, weight in grams, which crate it was assigned to, and whether it passed or failed the grade. Companies can log in and watch their order being filled in real time.

### Key Features
- 🏢 **Company self-service** — Buyers register, log in, place orders, and watch progress live
- ⚖️ **Per-mango audit trail** — Every reading stored with timestamp, weight, pass/fail status
- 📦 **Crate-level tracking** — Each physical crate maps to an order via an MQTT topic
- 🚦 **Real-time dashboards** — WebSocket updates as the scale fires readings
- 👮 **Admin oversight** — Admin manages companies, crate classes, crate assignments, and reports
- 📄 **Export reports** — CSV/PDF proof-of-weight for any order

---

## Architecture

```
┌─────────────────────────────────┐     MQTT      ┌──────────────────┐
│   ESP32 Scale (Hardware)        │ ────────────▶ │  MQTT Broker     │
│  • Reads touch sensor           │               │  (Mosquitto/HiveMQ)│
│  • Publishes to data/{crate_id} │               └────────┬─────────┘
└─────────────────────────────────┘                        │
                                                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Backend — FastAPI (Python 3.11)                                      │
│  • Receives MQTT readings via Node-RED or backend subscriber         │
│  • Validates weight against crate class range                        │
│  • Updates crate counted, order current_amount                       │
│  • Pushes real-time update via WebSocket (Socket.IO)                 │
├──────────────────────────────────────────────────────────────────────┤
│  Frontend — Nuxt 4 (Vue 3)                                           │
│  • Company dashboard: live order progress                            │
│  • Admin panel: manage all companies, crates, classes, reports       │
│  • Login with JWT authentication                                     │
└──────────────────────────────────────────────────────────────────────┘
                     │
              PostgreSQL Database
```

---

## Prerequisites

| Tool        | Version   | Install Link |
|-------------|-----------|--------------|
| Python      | 3.11+     | [python.org](https://www.python.org/downloads/) |
| Node.js     | 20+       | [nodejs.org](https://nodejs.org/) |
| pnpm        | 10+       | `npm i -g pnpm` |
| PostgreSQL  | 14+       | [postgresql.org](https://www.postgresql.org/download/) |

> **Windows users:** If you encounter build errors during `pip install`, install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (select "Desktop development with C++") and [Rust](https://www.rust-lang.org/tools/install), then restart your terminal.

---

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/golden-mango-weighing-system.git
cd golden-mango-weighing-system
```

### 2. Backend Setup

```bash
cd backend

# Create a virtual environment (use py -3.11 on Windows)
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Open .env and fill in your database URL, secret key, etc.
```

Edit `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://YOUR_USER:YOUR_PASSWORD@localhost:5432/golden_mango_db
SECRET_KEY=your-very-long-random-secret-key-here
```

```bash
# Run database migrations
alembic upgrade head

# Create the admin account and seed data
python scripts/setup_system.py --all

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

✅ Backend API is now running at `http://localhost:8000`
✅ API docs (Swagger) at `http://localhost:8000/docs`

### 3. Frontend Setup

Open a **new terminal**:

```bash
cd frontend

# Install dependencies
pnpm install

# Configure environment
# Create a file called .env in the frontend/ folder:
echo "NUXT_PUBLIC_API_URL=http://localhost:8000/api" > .env
echo "NUXT_PUBLIC_WS_URL=ws://localhost:8000" >> .env

# Start the dev server
pnpm dev
```

✅ Frontend is now running at `http://localhost:3000`

---

## Navigating the Application

### Login Page (`/login`)
- All users (admin and companies) log in at `http://localhost:3000/login`
- Enter your **username** and **password**
- You'll be redirected to your appropriate dashboard

### Admin Dashboard
If you are the **admin** (system owner/exporter), you'll see:

| Section | Location | What to do |
|---------|----------|------------|
| **Dashboard** | `/dashboard` | Overview of all active orders and readings |
| **Companies** | `/company` | Approve/view all registered companies |
| **Crate Classes** | `/crate_class` | Define weight ranges (e.g. Class A: 300–400g) |
| **Orders** | `/order` | View all orders from all companies |
| **Crates** | `/crate` | Create crates and assign them to orders |
| **Readings** | `/reading` | Full log of every weight reading |
| **Settings** | `/settings` | Upload logo, set organization name |
| **Admin** | `/admin` | Manage users and system roles |

### Company Dashboard
If you are a **buyer/company**, you'll see:

| Section | Location | What to do |
|---------|----------|------------|
| **Dashboard** | `/dashboard` | Real-time progress of your orders |
| **My Orders** | `/order` | Create new orders, see order status |
| **Readings** | `/reading` | View all readings for your orders |
| **Reports** | `/reports` | Export your order data as CSV/PDF |

---

## User Roles

### Admin (Exporter / Owner)
- Single admin account, set up during initial installation
- Full CRUD access to all data
- Manages: companies, crate classes, crate assignment, system settings
- Can generate reports for any company

### Company (Buyer)
- Self-registers via `/api/auth/register` or the registration form
- Can only see and interact with **their own** orders and readings
- Can create orders specifying crate class and quantity
- Watches real-time grading progress

---

## Data Model

```
company          order              crate_class
────────         ─────              ───────────
id               id                 id
name             company_id ──────▶ company    name
contact_person   crate_class_id ──▶ crate_class min_weight (g)
email            total_amount       max_weight (g)
phone            current_amount
address          status
status           (pending/
user_id ──▶ User  in-progress/
                  completed/
                  shipped)

crate            reading
─────            ───────
id               id
code             crate_id ──▶ crate
order_id ──▶     order_id ──▶ order
  order          weight_grams
crate_class_id   recorded_at
target           valid (bool)
counted
```

---

## Hardware Integration (ESP32 / MQTT)

The ESP32 on the packing floor:
1. Reads a mango weight from the load cell (converted to grams)
2. When the grader presses the button, publishes to:
   ```
   Topic: data/{crate_id}
   Payload: 385
   ```
3. The backend (or Node-RED bridge) receives this, looks up the crate's class weight range, marks the reading as valid or invalid, and updates the order progress

**Feedback loop:** If the reading is out of range, a rejection message is sent back to the ESP32's display:
```
"Failed. Send to crate 0F3242F"
```

---

<!--
## API Reference

Full interactive docs: `http://localhost:8000/docs`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/boot` | Login (returns token + sidebar + branding) |
| `POST` | `/api/auth/register` | Register a new company |
| `POST` | `/api/auth/login_company` | Company JSON login (returns JWT) |
| `GET`  | `/api/auth/me` | Get current user info |
| `POST` | `/api/auth/refresh` | Refresh access token |

### Example: Register a Company
```http
POST /api/auth/register
Content-Type: application/json

{
  "company_name": "Osaka Fruit Importers",
  "contact_person": "Taro Tanaka",
  "email": "taro@osakaimports.jp",
  "password": "securepassword123"
}
```

### Example: Create an Order
```http
POST /api/entity/order/new
Authorization: Bearer <your-jwt-token>
Content-Type: application/json

{
  "company": "your-company-id",
  "crate_class": "class-a-id",
  "total_amount": 500,
  "status": "pending"
}
```

---

## Git Setup Guide

Follow these steps to create a GitHub repository for this project and push the code safely.

### Step 1: Initialize Git (if not already a repo)
Open a terminal in the project root:
```bash
git init
git add .
git commit -m "Initial commit: Golden Mango Weighing System"
```

### Step 2: Create the GitHub Repository
1. Go to [github.com/new](https://github.com/new)
2. Enter the repository name: `golden-mango-weighing-system`
3. Set visibility to **Private** (recommended — this is a business system)
4. **Do NOT** check "Add README", "Add .gitignore", or "Choose a license" (we already have these)
5. Click **Create repository**

### Step 3: Connect and Push
Copy the commands GitHub shows you under "…or push an existing repository from the command line":
```bash
git remote add origin https://github.com/YOUR_USERNAME/golden-mango-weighing-system.git
git branch -M main
git push -u origin main
```

### Step 4: Verify Nothing Sensitive Was Committed
Before pushing, double-check by running:
```bash
git status
git log --oneline
```

Also verify these files do **NOT** appear in the push:
- `backend/.env` — contains your database password and secret key
- `backend/uploads/` — contains uploaded files
- `backend/.venv/` or `.venv311/` — Python virtual environment
- `frontend/node_modules/` — Node packages
- `frontend/.env` — frontend environment variables

The `.gitignore` in this project already blocks all of these. ✅

### Step 5: Set Up a Collaborator (Optional)
1. In your GitHub repo, go to **Settings → Collaborators**
2. Click **Add people** and enter their GitHub username
3. They will receive an email invitation

### Step 6: Environment Variables for New Clones
Whenever a new developer clones this repo, they will need to create their own `.env` file:
```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your own DB credentials and secret key

# Frontend  
echo "NUXT_PUBLIC_API_URL=http://localhost:8000/api" > frontend/.env
```

> ⚠️ **Never commit `.env` files** — they contain database passwords, JWT secret keys, and SMTP credentials that must stay private.

---


-->## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 4, Vue 3, Nuxt UI, Pinia, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy (async), Alembic, Python 3.11 |
| Database | PostgreSQL 14+ |
| Real-time | Socket.IO (WebSockets) |
| Auth | JWT (access + refresh tokens via httpOnly cookie) |
| Hardware | ESP32 + MQTT (Mosquitto / HiveMQ) |

---

## License

This project is proprietary software for internal use by the mango export business. Do not distribute without permission.
