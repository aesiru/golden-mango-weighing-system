#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_VENV="$BACKEND_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

SKIP_BACKEND_INSTALL=false
SKIP_FRONTEND_INSTALL=false
SKIP_FRONTEND_BUILD=false
SKIP_ADMIN=false  # CI/automation only; interactive admin creation is the default

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-backend-install)
            SKIP_BACKEND_INSTALL=true
            shift
            ;;
        --skip-frontend-install)
            SKIP_FRONTEND_INSTALL=true
            shift
            ;;
        --skip-frontend-build)
            SKIP_FRONTEND_BUILD=true
            shift
            ;;
        --skip-admin)
            # Bypass admin creation (CI/automation only — not recommended for production)
            SKIP_ADMIN=true
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Collected interactively before any install step so the process runs unattended
ADMIN_USERNAME=""
ADMIN_EMAIL=""
ADMIN_FULL_NAME=""
ADMIN_PASSWORD=""

ensure_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

ensure_pnpm() {
    if command -v pnpm >/dev/null 2>&1; then
        return
    fi

    ensure_command corepack
    corepack enable
    corepack prepare pnpm@10.28.1 --activate
}

# ── Collect all credentials upfront ─────────────────────────────────────────
# Both prompts run BEFORE any install step so the long install runs unattended.

prompt_postgres_bootstrap() {
    # If already set in environment, respect it.
    if [[ -n "${DATABASE_BOOTSTRAP_URL:-}" ]]; then
        echo "  Using DATABASE_BOOTSTRAP_URL from environment."
        return
    fi

    echo ""
    echo "PostgreSQL Bootstrap"
    echo "===================="
    echo "The installer must connect as a PostgreSQL superuser to create:"
    echo "  - the generated application role"
    echo "  - the generated application database"
    echo ""
    echo "What to enter:"
    echo "  - Host: usually localhost"
    echo "  - Port: usually 5432"
    echo "  - Username: usually postgres"
    echo "  - Password: the password for that PostgreSQL superuser"
    echo ""
    echo "Important: pressing Enter for everything does NOT work on most servers."
    echo "Leave the password blank only if this machine is already configured for"
    echo "passwordless peer/trust login as a PostgreSQL superuser. That is common"
    echo "on some local dev machines, but uncommon on production servers."
    echo ""
    echo "If you do not know these credentials, stop here and ask whoever manages"
    echo "PostgreSQL on this server."
    echo ""

    local pg_host pg_port pg_user pg_pass
    read -r -p "  Superuser host     [localhost]: " pg_host
    pg_host="${pg_host:-localhost}"

    read -r -p "  Superuser port     [5432]:     " pg_port
    pg_port="${pg_port:-5432}"

    read -r -p "  Superuser username [postgres]: " pg_user
    pg_user="${pg_user:-postgres}"

    read -r -s -p "  Superuser password (blank = peer auth): " pg_pass
    echo ""

    if [[ -z "$pg_pass" ]]; then
        export DATABASE_BOOTSTRAP_URL="postgresql:///postgres"
        echo "  → Using passwordless OS peer auth for bootstrap."
        echo "    This will fail unless the current Unix user can already connect"
        echo "    to PostgreSQL as a superuser without a password."
    else
        export DATABASE_BOOTSTRAP_URL="postgresql://${pg_user}:${pg_pass}@${pg_host}:${pg_port}/postgres"
        echo "  → Bootstrap URL set (password hidden)."
    fi
}

prompt_admin_credentials() {
    if [[ "$SKIP_ADMIN" == true ]]; then
        return
    fi

    echo ""
    echo "Administrator Account"
    echo "====================="
    echo "Create the first administrator account for this EAM installation."
    echo ""

    local username email full_name pass1 pass2

    read -r -p "  Username   [admin]: " username
    ADMIN_USERNAME="${username:-admin}"

    while true; do
        read -r -p "  Email            : " email
        if [[ -n "$email" ]]; then
            ADMIN_EMAIL="$email"
            break
        fi
        echo "  Email is required."
    done

    while true; do
        read -r -p "  Full name        : " full_name
        if [[ -n "$full_name" ]]; then
            ADMIN_FULL_NAME="$full_name"
            break
        fi
        echo "  Full name is required."
    done

    while true; do
        read -r -s -p "  Password         : " pass1
        echo ""
        if [[ -z "$pass1" ]]; then
            echo "  Password is required."
            continue
        fi
        read -r -s -p "  Confirm password : " pass2
        echo ""
        if [[ "$pass1" == "$pass2" ]]; then
            ADMIN_PASSWORD="$pass1"
            break
        fi
        echo "  Passwords do not match. Try again."
    done

    echo "  → Administrator '${ADMIN_USERNAME}' will be created after DB bootstrap."
}

# ── Site credential generation ────────────────────────────────────────────────
# Generates a unique SITE_ID and derives DB_NAME, DB_ROLE, DB_PASSWORD, SECRET_KEY.
# Skipped if backend/.env already exists (idempotent re-runs).

SITE_ID=""
DB_NAME=""
DB_ROLE=""
DB_PASSWORD=""
SECRET_KEY=""

generate_site_credentials() {
    SITE_ID="$(openssl rand -hex 6)"
    DB_NAME="eam_${SITE_ID}"
    DB_ROLE="eam_${SITE_ID}"
    DB_PASSWORD="$(openssl rand -base64 32 | tr -d '=+/')"
    SECRET_KEY="$(openssl rand -base64 48 | tr -d '=+/')"

    echo ""
    echo "  Generated site credentials:"
    echo "    DB name / role : ${DB_NAME}"
    echo "    DB password    : (hidden)"
    echo "    Secret key     : (hidden)"
}

write_backend_env() {
    local env_file="$BACKEND_DIR/.env"

    if [[ -f "$env_file" ]]; then
        echo "  backend/.env already exists — skipping credential generation."
        return
    fi

    generate_site_credentials

    cat > "$env_file" <<EOF
# ============================================================
# EAM System — Generated by install.sh on $(date -u '+%Y-%m-%dT%H:%M:%SZ')
# DO NOT COMMIT THIS FILE.
# ============================================================

# ── Database ─────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://${DB_ROLE}:${DB_PASSWORD}@localhost:5432/${DB_NAME}
# DATABASE_URL_SYNC is auto-derived from DATABASE_URL when omitted.

# ── Security ─────────────────────────────────────────────────
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── CORS ─────────────────────────────────────────────────────
# CORS_ORIGINS=["http://localhost:3000"]
# SOCKETIO_CORS_ORIGINS=["http://localhost:3000"]

# ── File Uploads ─────────────────────────────────────────────
# UPLOAD_DIR=uploads
# MAX_UPLOAD_SIZE_MB=10

# ── Email / SMTP (optional) ─────────────────────────────────
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USE_TLS=true
# SMTP_USERNAME=
# SMTP_PASSWORD=
# EMAIL_FROM_ADDRESS=
# EMAIL_ENABLED=false
EOF

    echo "  backend/.env written."
}

ensure_frontend_env() {
    local env_file="$FRONTEND_DIR/.env"
    if [[ -f "$env_file" ]]; then
        return
    fi

    cat > "$env_file" <<EOF
NUXT_PUBLIC_API_URL=${NUXT_PUBLIC_API_URL:-http://localhost:8000/api}
NUXT_PUBLIC_WS_URL=${NUXT_PUBLIC_WS_URL:-http://localhost:8000}
EOF
}

install_backend() {
    ensure_command "$PYTHON_BIN"
    cd "$BACKEND_DIR"

    if [[ ! -d "$BACKEND_VENV" ]]; then
        "$PYTHON_BIN" -m venv "$BACKEND_VENV"
    fi

    source "$BACKEND_VENV/bin/activate"
    python -m pip install --upgrade pip wheel setuptools
    pip install -r requirements.txt
}

install_frontend() {
    ensure_command node
    ensure_pnpm

    cd "$FRONTEND_DIR"
    pnpm install

    if [[ "$SKIP_FRONTEND_BUILD" != true ]]; then
        pnpm build
    fi
}

run_backend_bootstrap() {
    cd "$BACKEND_DIR"
    source "$BACKEND_VENV/bin/activate"

    local setup_args=("--all")

    if [[ "$SKIP_ADMIN" == true ]]; then
        setup_args+=("--skip-admin")
    else
        # Credentials were collected upfront — pass explicitly so no TTY is needed here.
        setup_args+=(
            "--admin-username" "$ADMIN_USERNAME"
            "--admin-email"    "$ADMIN_EMAIL"
            "--admin-full-name" "$ADMIN_FULL_NAME"
            "--admin-password" "$ADMIN_PASSWORD"
        )
    fi

    python scripts/setup_system.py "${setup_args[@]}"
}

main() {
    echo ""
    echo "EAM Install"
    echo "==========="
    echo "Collecting setup information before installation begins."

    prompt_postgres_bootstrap
    prompt_admin_credentials

    echo ""
    echo "[0/3] Preparing environment files"
    write_backend_env
    ensure_frontend_env

    if [[ "$SKIP_BACKEND_INSTALL" != true ]]; then
        echo ""
        echo "[1/3] Installing backend dependencies"
        install_backend
    fi

    if [[ "$SKIP_FRONTEND_INSTALL" != true ]]; then
        echo ""
        echo "[2/3] Installing frontend dependencies"
        install_frontend
    fi

    echo ""
    echo "[3/3] Bootstrapping database and application"
    run_backend_bootstrap

    echo ""
    echo "Install complete."
    echo "Start the app with: ./run.sh"
}

main