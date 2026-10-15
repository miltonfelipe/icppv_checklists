# icppv_checklists
Checklists apps for ICPPV

## Running the server

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
uvicorn app.main:app --reload
```

Once it's running, open:

- **http://localhost:8000/** for the checklist (open to everyone): active items grouped by group, in `sequence` order; pick a checklist (`type`) from the dropdown or "All"; click an item to mark it done (sets `activated`), click again to undo
- **http://localhost:8000/admin** for the editor (asks for the admin login): create, edit and delete items, and reset a checklist (mark all its items as not done)
- **http://localhost:8000/docs** for the interactive API docs

### Admin login

Creating, editing and deleting items (the `/admin` page and the `POST`/`PUT`/`DELETE /items` API) require the
login set by `ICPPV_ADMIN_USER` / `ICPPV_ADMIN_PASSWORD`. If no password is set, editing is disabled.
Reading items and marking them done/not done stay open.

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

# Needed for create / update / delete (marking items done with `update ID --activated` works without it)
export ICPPV_ADMIN_USER=admin
export ICPPV_ADMIN_PASSWORD='the-server-password'
```
