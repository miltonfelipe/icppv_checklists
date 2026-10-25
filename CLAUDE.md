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

# Run the server (reloads on file change); editing needs an admin password
export ICPPV_ADMIN_PASSWORD='choose-a-password'   # ICPPV_ADMIN_USER defaults to "admin"
uvicorn app.main:app --reload

# Run on a specific port
uvicorn app.main:app --reload --port 8080
```

Once the server is running:
- Checklist UI (open): `http://localhost:8000/`
- Editor UI (admin login): `http://localhost:8000/admin`
- Interactive API docs: `http://localhost:8000/docs`

## Architecture

```
app/
  database.py   SQLAlchemy engine, session factory, and get_db dependency
  models.py     ORM model (ChecklistItem) + Pydantic schemas (ItemCreate, ItemUpdate, ItemResponse)
  main.py       FastAPI app; creates tables on startup, defines all routes, HTTP Basic admin auth (require_admin)
  static/admin.html  Editor UI at /admin (plain HTML/JS, no build step) that calls the /items API
  static/checklist.html  Checklist UI: dropdown selects a `type` (or All, kept in `?type=`); shows active items' descriptions (with their `time`, if any, on the right) grouped by group, ordered by `time`, then `sequence`; clicking toggles `activated` via the open PUT /items/{id}/activated; re-fetches every 30 s and when the tab becomes visible; pending items turn yellow from 5 min before their `time` and red once it's reached (device clock)
client/
  api.py        Thin requests wrapper (ChecklistClient) — usable as a library
  cli.py        Typer CLI; each command delegates to ChecklistClient
  requirements.txt
checklists.db   SQLite file created at runtime in the repo root
```

The database has a single table `items` with columns: `id, type, group, description, active, activated, time, sequence`. `active` and `activated` are booleans; `time` is an optional time of day at which the task must be performed, always 24-hour `HH:MM` text in the API, web UI and CLI (validated and serialized by the `Clock` type in `models.py`; stored as SQLite TIME); `sequence` is an optional integer giving the item's position in its checklist (items without one sort last). `GET /items` returns items ordered by `time` (items without one last), then `sequence`, then `id`.

`group` is a SQL reserved word — the ORM column is declared with an explicit name `Column("group", String)` so SQLAlchemy quotes it correctly.

## Client setup (remote machine)

```bash
# Copy just the client/ directory to the remote machine, then:
sudo apt install python3-pip python3-venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r client/requirements.txt

# Point at the server (set once, or pass --url on every command)
export ICPPV_SERVER_URL=http://<server-ip>:8000
# Needed for create/update/delete (update with only --activated/--no-activated works without it)
export ICPPV_ADMIN_USER=admin ICPPV_ADMIN_PASSWORD='the-server-password'

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
| POST | `/items/reset` | Set `activated = false` on all items, or only `?type=`; returns `{"reset": n}` (admin) |
| PUT | `/items/{id}` | Partial update (admin) |
| PUT | `/items/{id}/activated` | Set only `activated`, body `{"activated": true}` (open; 404 for inactive items) |
| DELETE | `/items/{id}` | Delete (204) (admin) |

"(admin)" routes require HTTP Basic auth matching `ICPPV_ADMIN_USER` (default `admin`) / `ICPPV_ADMIN_PASSWORD`; with no password set they return 503.
