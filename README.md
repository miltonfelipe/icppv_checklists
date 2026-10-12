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

# Every time: activate the venv and start the server
source .venv/bin/activate
uvicorn app.main:app --reload
```

Once it's running, open:

- **http://localhost:8000/** for the web UI to edit items
- **http://localhost:8000/docs** for the interactive API docs

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
```
