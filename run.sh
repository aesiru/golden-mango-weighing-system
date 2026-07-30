#!/bin/bash

# EAM Launcher
# Starts backend and frontend, or runs the full installer.
#
# Usage:
#   ./run.sh                    — start backend + frontend
#   ./run.sh install [args...]  — install deps + bootstrap DB/tables/admin
#   ./run.sh setup [args...]    — backend-only bootstrap (DB/tables/seeds/admin)
#
# Local DB credentials (eam_local_dev @ 127.0.0.1:5432):
#   DB name : eam_local_dev
#   User    : eam_dev
#   Password: EamDev2026Dev

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ── Activate venv helper ────────────────────────────────────────────────────
_activate_venv() {
    cd "$BACKEND_DIR"
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    fi

    pip install -r requirements.txt -q
}

_ensure_pnpm() {
    if command -v pnpm >/dev/null 2>&1; then
        return
    fi

    corepack enable
    corepack prepare pnpm@10.28.1 --activate
}

if [ "${1:-}" = "install" ]; then
    echo -e "${GREEN}EAM Full Install${NC}"
    echo "============================================"
    "$PROJECT_DIR/install.sh" "${@:2}"
    exit 0
fi

# ── Setup mode (run setup_system.py and exit) ───────────────────────────────
if [ "${1:-}" = "setup" ]; then
    echo -e "${GREEN}EAM Backend Bootstrap${NC}"
    echo "============================================"
    _activate_venv
    if [ "$#" -eq 1 ]; then
        set -- setup --all
    fi
    echo -e "${YELLOW}Running backend bootstrap...${NC}"
    python scripts/setup_system.py "${@:2}"
    echo ""
    echo -e "${GREEN}Setup complete. Run './run.sh' to start servers.${NC}"
    exit 0
fi

# ── Normal dev server mode ──────────────────────────────────────────────────
# Ensure backend/.env exists before starting (copy from .env.example if missing)
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    if [[ -f "$PROJECT_DIR/.env.example" ]]; then
        echo -e "${YELLOW}Creating backend/.env from .env.example...${NC}"
        cp "$PROJECT_DIR/.env.example" "$BACKEND_DIR/.env"
    else
        echo -e "${RED}ERROR: backend/.env not found and no .env.example to copy from.${NC}" >&2
        exit 1
    fi
fi

echo -e "${GREEN}Starting EAM Development Servers${NC}"
echo "============================================"

# Kill existing processes on ports 8000 and 3000
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Start Backend
echo -e "${GREEN}Starting Backend (FastAPI) on port 8000...${NC}"
_activate_venv
uvicorn app.main:app --reload --port 8000 \
  --reload-exclude 'backups/*' \
  --reload-exclude 'alembic/versions/*' \
  --reload-exclude '*/models/*.py' &
BACKEND_PID=$!

# Start Frontend
echo -e "${GREEN}Starting Frontend (Nuxt) on port 3000...${NC}"
cd "$FRONTEND_DIR"
_ensure_pnpm
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pnpm install
fi
pnpm dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Servers started successfully!${NC}"
echo -e "  Backend:  ${YELLOW}http://localhost:8000${NC}"
echo -e "  Frontend: ${YELLOW}http://localhost:3000${NC}"
echo -e "  API Docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "  DB:       ${YELLOW}eam_local_dev @ 127.0.0.1:5432${NC}  (user: eam_dev)"
echo -e "  Install:  ${YELLOW}./run.sh install${NC}"
echo -e "  Setup:    ${YELLOW}./run.sh setup --interactive${NC}  (backend-only)"
echo -e "  Tests:    ${YELLOW}cd backend && pytest tests/setup/ -v${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop all servers"

# Trap Ctrl+C to kill both processes
trap "echo -e '\n${RED}Stopping servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for processes
wait
