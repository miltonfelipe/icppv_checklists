# icppv_checklists
Checklists apps for ICPPV

## Running the server

### Quick start

```bash
cp .env.example .env      # then edit .env and set ICPPV_ADMIN_PASSWORD
./start.sh                # or ./start.sh --dev to auto-reload on code changes
```

`start.sh` creates `.venv` and installs dependencies on first run, loads `.env`, and starts the server on
`ICPPV_HOST`/`ICPPV_PORT` (default `0.0.0.0:8000`, so other machines can reach it). Extra arguments are passed to uvicorn.

### Run as a service (start at boot)

```bash
./install-service.sh                 # installs the systemd service icppv-checklists (asks for sudo)
journalctl -u icppv-checklists -f    # logs
sudo systemctl restart icppv-checklists   # after editing .env or updating the code
./install-service.sh --uninstall     # remove it
```

The service runs `start.sh` from the repo directory as your user, so it uses the same `.env`. If there is no `.env` yet, the installer
creates one with the default admin password `162543`; change it in `.env` and restart the service.

`./client.sh <command>` runs the CLI client the same way (e.g. `./client.sh list --type safety`).

### Manual setup

From the repo root:

```bash
# First time only: install system packages, create the venv and install dependencies
sudo apt install python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Every time: activate the venv, set the admin login and start the server
source .venv/bin/activate
export ICPPV_ADMIN_USER=admin              # optional, defaults to "admin"
export ICPPV_ADMIN_PASSWORD='choose-a-password'
export ICPPV_PIN=1234                      # 4-digit PIN for ticking/snoozing items on the checklist
uvicorn app.main:app --reload
```

Once it's running, open:

- **http://localhost:8000/** for the checklist (anyone can view it; ticking or snoozing items asks for the PIN; every item is unticked and un-snoozed automatically at the start of each day, server time): active items grouped by group, in `sequence` order; pick a checklist (`type`) from the dropdown or "All"; click an item to mark it done (sets `activated`), click again to undo; pending items turn yellow 1 minute before their `time` and red once it has passed
- **http://localhost:8000/admin** for the editor (asks for the admin login): create, edit and delete items, and reset a checklist (mark all its items as not done)
- **http://localhost:8000/report** for the daily activity report (asks for the admin login): for each day, every item ticked done (and undone, snoozed or reset) with the time it happened, the time it was due and how early or late it was; filter by checklist
- **http://localhost:8000/docs** for the interactive API docs

### Admin login

Creating, editing and deleting items (the `/admin` page and the `POST`/`PUT`/`DELETE /items` API) require the
login set by `ICPPV_ADMIN_USER` / `ICPPV_ADMIN_PASSWORD`. If no password is set, editing is disabled.
Reading items stays open.

### Checklist PIN

Marking items done/not done and snoozing them (on the checklist page, or `PUT /items/{id}/activated` and
`/snooze` in the API) need the 4-digit PIN set by `ICPPV_PIN`; the admin login works too. `start.sh` (and so the
systemd service) uses 2543 unless `ICPPV_PIN` is set in the environment or `.env`; when running uvicorn
directly with no valid PIN set, these actions are disabled. The checklist page asks for the PIN on the first tap and remembers it until
the tab is closed (or "Lock" is clicked). After 5 wrong PINs in a row, PIN entry is blocked for everyone for
5 minutes. Restart the server after changing the PIN.

The login uses HTTP Basic auth, so over plain `http://` the password is not encrypted. If the server is reachable
from the internet, put it behind HTTPS (e.g. a reverse proxy such as Caddy or nginx).

### Options

- **Different port:** add `--port 8080`.
- **Remote machines:** the server only listens on localhost by default. If you'll use the CLI client from another machine, add `--host 0.0.0.0` so it can reach the server:

  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

## CLI client

On the client machine (only the `client/` directory is needed):

```bash
sudo apt install python3-pip python3-venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r client/requirements.txt

export ICPPV_SERVER_URL=http://<server-ip>:8000
python3 -m client --help

# Needed for create / update / delete
export ICPPV_ADMIN_USER=admin
export ICPPV_ADMIN_PASSWORD='the-server-password'
# Or, to only mark items done/snooze them (`update ID --activated` / `--snooze`), just the checklist PIN
export ICPPV_PIN=1234
```
