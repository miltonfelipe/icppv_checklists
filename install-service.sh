#!/usr/bin/env bash
# Install (or remove) the ICPPV Checklists server as a systemd service.
#
# Usage:
#   ./install-service.sh              install, enable at boot and start
#   ./install-service.sh --uninstall  stop, disable and remove the service
#
# The service runs ./start.sh from this directory as the user who runs this
# script, so settings (admin password, host, port) come from .env here.
# If there is no .env, one is created from .env.example with the admin
# password set to DEFAULT_ADMIN_PASSWORD below.
# Uses sudo for the systemd steps.
#
# Afterwards:
#   systemctl status icppv-checklists       is it running?
#   journalctl -u icppv-checklists -f       follow the logs
#   sudo systemctl restart icppv-checklists after editing .env or updating the code
set -euo pipefail

SERVICE=icppv-checklists
UNIT=/etc/systemd/system/$SERVICE.service
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_USER="${SUDO_USER:-$(id -un)}"
# Admin password written to .env when no .env exists yet (an existing .env is never changed).
DEFAULT_ADMIN_PASSWORD=162543

if [[ "$RUN_USER" == root ]]; then
    echo "Run this as the user that should own the service (it calls sudo itself), not as root." >&2
    exit 1
fi

SUDO=sudo
[[ $EUID -eq 0 ]] && SUDO=

if ! command -v systemctl >/dev/null; then
    echo "systemd (systemctl) not found; this script needs a systemd-based Linux." >&2
    exit 1
fi

if [[ "${1:-}" == "--uninstall" ]]; then
    $SUDO systemctl disable --now "$SERVICE" 2>/dev/null || true
    $SUDO rm -f "$UNIT"
    $SUDO systemctl daemon-reload
    echo "Removed $SERVICE."
    exit 0
fi

if ! python3 -c 'import venv, ensurepip' 2>/dev/null; then
    echo "python3-venv is missing; install it with: sudo apt install python3-pip python3-venv" >&2
    exit 1
fi

if [[ ! -f "$ROOT/.env" ]]; then
    echo "No .env found; creating one with the default admin password ($DEFAULT_ADMIN_PASSWORD)."
    echo "Change it by editing .env, then: sudo systemctl restart $SERVICE"
    sed "s/^ICPPV_ADMIN_PASSWORD=.*/ICPPV_ADMIN_PASSWORD=$DEFAULT_ADMIN_PASSWORD/" \
        "$ROOT/.env.example" > "$ROOT/.env"
    chmod 600 "$ROOT/.env"
    if [[ $EUID -eq 0 ]]; then chown "$RUN_USER": "$ROOT/.env"; fi
fi

# Set up the venv now, as the service user, so dependency errors show up here
# rather than in the service log.
echo "Preparing virtual environment ..."
AS_USER=()
[[ $EUID -eq 0 ]] && AS_USER=(sudo -u "$RUN_USER")
"${AS_USER[@]}" bash -c '
    set -e
    cd "$1"
    [ -x .venv/bin/python ] || python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    touch .venv/.requirements.installed
' _ "$ROOT"

echo "Writing $UNIT ..."
$SUDO tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=ICPPV Checklists server
Wants=network-online.target
After=network-online.target

[Service]
Type=exec
User=$RUN_USER
WorkingDirectory=$ROOT
ExecStart=$ROOT/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

$SUDO systemctl daemon-reload
$SUDO systemctl enable "$SERVICE"
$SUDO systemctl restart "$SERVICE"

sleep 2
if systemctl is-active --quiet "$SERVICE"; then
    echo "$SERVICE is running and will start at boot."
    echo "Logs: journalctl -u $SERVICE -f"
else
    echo "$SERVICE failed to start; recent log:" >&2
    $SUDO journalctl -u "$SERVICE" -n 20 --no-pager >&2
    exit 1
fi
