#!/usr/bin/env bash
# Start the ICPPV Checklists server.
#
# Usage: ./start.sh [--dev] [extra uvicorn args...]
#   --dev   auto-reload on code changes (development)
#
# Settings come from the environment, or from a .env file next to this script
# (see .env.example):
#   ICPPV_ADMIN_PASSWORD  admin password (editing is disabled if unset)
#   ICPPV_ADMIN_USER      admin user name (default: admin)
#   ICPPV_PIN             4-digit PIN to tick/snooze checklist items (default: 2543)
#   ICPPV_HOST            interface to listen on (default: 0.0.0.0)
#   ICPPV_PORT            port (default: 8000)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"   # the SQLite database (checklists.db) lives in the repo root

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi
export ICPPV_PIN="${ICPPV_PIN:-2543}"   # default checklist PIN

if [[ -z "${ICPPV_ADMIN_PASSWORD:-}" ]]; then
    echo "Warning: ICPPV_ADMIN_PASSWORD is not set; the /admin editor will be disabled." >&2
fi
if [[ ! "${ICPPV_PIN:-}" =~ ^[0-9]{4}$ ]]; then
    echo "Warning: ICPPV_PIN is not 4 digits; ticking and snoozing checklist items will be disabled." >&2
fi

ARGS=(--host "${ICPPV_HOST:-0.0.0.0}" --port "${ICPPV_PORT:-8000}")
if [[ "${1:-}" == "--dev" ]]; then
    ARGS+=(--reload)
    shift
fi

echo "Starting ICPPV Checklists on http://${ICPPV_HOST:-0.0.0.0}:${ICPPV_PORT:-8000}/ (admin: /admin)"
exec python3 -m uvicorn app.main:app "${ARGS[@]}" "$@" && tailscale funnel --bg 8000
