#!/usr/bin/env bash
# Run the ICPPV Checklists CLI client, e.g.:  ./client.sh list --type safety
#
# Settings come from the environment, or from a .env file next to this script:
#   ICPPV_SERVER_URL      server address (default: http://localhost:8000)
#   ICPPV_ADMIN_USER / ICPPV_ADMIN_PASSWORD   needed for create/update/delete
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

if [[ ! -x .venv/bin/python ]]; then
    echo "Creating virtual environment in .venv ..." >&2
    python3 -m venv .venv
fi
STAMP=.venv/.client-requirements.installed
if [[ ! -f "$STAMP" || client/requirements.txt -nt "$STAMP" ]]; then
    echo "Installing client dependencies ..." >&2
    .venv/bin/pip install -q -r client/requirements.txt
    touch "$STAMP"
fi

exec .venv/bin/python -m client "$@"
