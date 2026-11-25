# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI + SQLite web server that exposes CRUD operations over a checklist items table for ICPPV, plus a standalone CLI client for use on remote machines.

## Commands

```bash
# One-time system setup (Debian/Ubuntu)
sudo apt install python3-pip python3-venv

# Install dependencies (inside a venv is recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start scripts: create .venv + install deps on first run, load .env (see .env.example)
./start.sh             # server on ICPPV_HOST:ICPPV_PORT (default 0.0.0.0:8000); --dev adds --reload
./client.sh list       # CLI client
./install-service.sh   # systemd service "icppv-checklists" running start.sh as the current user (--uninstall removes it)
python3 make_icons.py  # redraw the PNG phone icons in app/static/ after changing icon.svg (needs Pillow)

# Run the server (reloads on file change); editing needs an admin password
export ICPPV_ADMIN_PASSWORD='choose-a-password'   # ICPPV_ADMIN_USER defaults to "admin"
export ICPPV_PIN=1234                             # 4-digit PIN to tick/snooze checklist items
uvicorn app.main:app --reload

# Run on a specific port
uvicorn app.main:app --reload --port 8080
```

Once the server is running:
- Checklist UI (view open, actions need the PIN): `http://localhost:8000/`
- Editor UI (admin login): `http://localhost:8000/admin`
- Daily activity report (admin login): `http://localhost:8000/report`
- Interactive API docs: `http://localhost:8000/docs`

## Architecture

```
app/
  database.py   SQLAlchemy engine, session factory, and get_db dependency
  models.py     ORM models (ChecklistItem, ActivityLog) + Pydantic schemas (ItemCreate, ItemUpdate, ItemResponse, LogResponse, LogDay)
  main.py       FastAPI app; creates tables on startup, defines all routes, HTTP Basic admin auth (require_admin), checklist PIN check (require_pin: X-ICPPV-PIN header or admin login; global 5-failure / 5-min lockout, in memory)
  static/icon.svg  App icon (served at /icon.svg and /favicon.ico); apple-touch-icon.png, icon-192.png, icon-512.png are PNG renders of it for phone home screens, listed in manifest.webmanifest (regenerate with `python3 make_icons.py`, which needs Pillow and must be kept in sync with the SVG by hand)
  static/report.html  Daily activity report at /report (admin): pick a day (from /logs/days) and optionally a type; tables per type of each logged event with its server time, the item's due time then, and how early/late a "done" was (ticking within the due minute is on time)
  static/admin.html  Editor UI at /admin (plain HTML/JS, no build step) that calls the /items API
  static/checklist.html  Checklist UI: dropdown selects a `type` (or All, kept in `?type=`); shows active items' descriptions (with their `time`, if any, on the right) grouped by group, ordered by `time`, then `sequence`; clicking toggles `activated` via PUT /items/{id}/activated; actions first ask for the PIN in a <dialog> (checked with POST /pin, kept in sessionStorage until the tab closes or "Lock" is clicked, re-asked on a 401); pending items with a time get a `+5` snooze button (and `↺` to undo it) that adds to the item's own `snooze` via PUT /items/{id}/snooze; an item's due time is pushed back by its own snooze plus those of all items of the same type with an earlier stored `time`, shown with the stored time struck through; re-fetches every 30 s and when the tab becomes visible; pending items turn yellow from 5 min before their `time` and red once it's reached (device clock)
client/
  api.py        Thin requests wrapper (ChecklistClient) — usable as a library
  cli.py        Typer CLI; each command delegates to ChecklistClient
  requirements.txt
checklists.db   SQLite file created at runtime in the repo root
```

The database has a single table `items` with columns: `id, type, group, description, active, activated, time, sequence`. `active` and `activated` are booleans; `time` is an optional time of day at which the task must be performed, always 24-hour `HH:MM` text in the API, web UI and CLI (validated and serialized by the `Clock` type in `models.py`; stored as SQLite TIME); `sequence` is an optional integer giving the item's position in its checklist (items without one sort last); `snooze` is the number of minutes checklist users have snoozed that item (default 0); it also shifts every item of the same type with a later `time`, so an item's effective due time is its `time` plus its own snooze and the snoozes of all items of its type with an earlier `time` (computed in checklist.html; the stored `time` never changes, and ordering ignores snoozes). `GET /items` returns items ordered by `time` (items without one last), then `sequence`, then `id`.

The `activity_log` table records checklist use for the report: one row per real change (`done`, `undone`, `snooze` with `minutes` = new snooze, admin `reset` with `minutes` = items reset), with `at` (server local time, to the second), `source` (`checklist` or `admin`), and copies of the item's `item_id, type, group, description` plus `due` (its effective due time at that moment, snoozes included; computed by `_effective_due` in main.py, mirroring checklist.html). Setting a value an item already has logs nothing. Rows are never deleted.

`group` is a SQL reserved word — the ORM column is declared with an explicit name `Column("group", String)` so SQLAlchemy quotes it correctly.

## Client setup (remote machine)

```bash
# Copy just the client/ directory to the remote machine, then:
sudo apt install python3-pip python3-venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r client/requirements.txt

# Point at the server (set once, or pass --url on every command)
export ICPPV_SERVER_URL=http://<server-ip>:8000
# Needed for create/update/delete
export ICPPV_ADMIN_USER=admin ICPPV_ADMIN_PASSWORD='the-server-password'
# Enough for update with only --activated/--no-activated and/or --snooze
export ICPPV_PIN=1234

# Run
python3 -m client --help
```

### CLI commands

```bash
python3 -m client list                          # all items
python3 -m client list --type safety --active
python3 -m client list --no-activated            # boolean filters: --active/--no-active, --activated/--no-activated
python3 -m client get 3
python3 -m client create                        # interactive prompts
python3 -m client create --type safety --group ops --description "Check valve"
python3 -m client update 3 --no-active
python3 -m client update 3 --activated
python3 -m client update 3 --time 08:30           # time of day the task must be performed
python3 -m client update 3 --sequence 2           # position in the checklist
python3 -m client update 3 --snooze 10            # postpone 10 min past its time (0 undoes)
python3 -m client delete 3
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Checklist UI (open) |
| GET | `/admin` | Editor UI (admin) |
| GET | `/checklist` | Redirects to `/` |
| GET | `/items` | List all items; filter via `?type=`, `?group=`, `?active=`, `?activated=` query params |
| GET | `/items/{id}` | Fetch a single item |
| POST | `/items` | Create an item (201) (admin) |
| POST | `/items/reset` | Set `activated = false` and `snooze = 0` on all items, or only `?type=`; returns `{"reset": n}` (admin) |
| PUT | `/items/{id}` | Partial update (admin) |
| GET | `/report` | Daily activity report UI (admin) |
| GET | `/logs/days` | Days with logged activity, newest first: `[{"date": "YYYY-MM-DD", "count": n}]` (admin) |
| GET | `/logs` | One day's activity log in time order; `?date=YYYY-MM-DD` (default today, server time), `?type=` (admin) |
| POST | `/pin` | Check a checklist PIN, body `{"pin": "1234"}`; 204 if right, 401 if wrong, 429 while locked out |
| PUT | `/items/{id}/activated` | Set only `activated`, body `{"activated": true}` (PIN; 404 for inactive items) |
| PUT | `/items/{id}/snooze` | Set only `snooze` (minutes past `time`, 0–1440), body `{"snooze": 10}` (PIN; 404 for inactive items, 422 if the item has no time) |
| DELETE | `/items/{id}` | Delete (204) (admin) |

"(admin)" routes require HTTP Basic auth matching `ICPPV_ADMIN_USER` (default `admin`) / `ICPPV_ADMIN_PASSWORD`; with no password set they return 503.
"(PIN)" routes require the 4-digit `ICPPV_PIN` in an `X-ICPPV-PIN` header (or the admin login); with no valid PIN set they return 503. The start scripts default `ICPPV_PIN` to 2543.
