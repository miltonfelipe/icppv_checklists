import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import (
    ActivatedUpdate,
    ChecklistItem,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    SnoozeUpdate,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ICPPV Checklists API")

STATIC_DIR = Path(__file__).parent / "static"
ADMIN_HTML = STATIC_DIR / "admin.html"
CHECKLIST_HTML = STATIC_DIR / "checklist.html"
ICON_SVG = STATIC_DIR / "icon.svg"

ADMIN_REALM = "ICPPV admin"
basic_auth = HTTPBasic(realm=ADMIN_REALM)


def _admin_ok(credentials: HTTPBasicCredentials, password: str) -> bool:
    user = os.environ.get("ICPPV_ADMIN_USER", "admin")
    user_ok = secrets.compare_digest(credentials.username.encode(), user.encode())
    password_ok = secrets.compare_digest(credentials.password.encode(), password.encode())
    return user_ok and password_ok


def require_admin(credentials: HTTPBasicCredentials = Depends(basic_auth)):
    """HTTP Basic auth against ICPPV_ADMIN_USER / ICPPV_ADMIN_PASSWORD.

    Editing is disabled entirely while no password is configured.
    """
    password = os.environ.get("ICPPV_ADMIN_PASSWORD")
    if not password:
        raise HTTPException(
            status_code=503,
            detail="Editing is disabled: set ICPPV_ADMIN_PASSWORD on the server",
        )
    if not _admin_ok(credentials, password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": f'Basic realm="{ADMIN_REALM}"'},
        )


# --- Checklist PIN -----------------------------------------------------------
# Anyone can view the checklist; ticking items and snoozing them needs the 4-digit
# ICPPV_PIN, sent in the X-ICPPV-PIN header (the admin login is accepted instead).
# A 4-digit PIN is easy to guess, so after PIN_MAX_FAILURES wrong PINs in a row all
# PIN checks are refused for PIN_LOCKOUT_SECONDS. The counter is global, not per
# client, because behind a proxy (e.g. tailscale funnel) every client has the same IP.
PIN_HEADER = "X-ICPPV-PIN"
PIN_MAX_FAILURES = 5
PIN_LOCKOUT_SECONDS = 5 * 60

_pin_lock = threading.Lock()
_pin_failures = 0
_pin_locked_until = 0.0

optional_basic_auth = HTTPBasic(auto_error=False)


def _configured_pin() -> str:
    pin = os.environ.get("ICPPV_PIN", "")
    if not re.fullmatch(r"\d{4}", pin):
        raise HTTPException(
            status_code=503,
            detail="Checklist actions are disabled: set ICPPV_PIN (4 digits) on the server",
        )
    return pin


def _check_pin(pin: str) -> None:
    """Raise 429 while locked out, 401 for a wrong PIN; counts failures."""
    global _pin_failures, _pin_locked_until
    expected = _configured_pin()
    with _pin_lock:
        wait = _pin_locked_until - time.monotonic()
        if wait > 0:
            minutes = -(-int(wait) // 60)
            raise HTTPException(
                status_code=429,
                detail=f"Too many wrong PINs; try again in {minutes} min",
                headers={"Retry-After": str(int(wait) + 1)},
            )
        if secrets.compare_digest(pin.encode(), expected.encode()):
            _pin_failures = 0
            return
        _pin_failures += 1
        if _pin_failures >= PIN_MAX_FAILURES:
            _pin_failures = 0
            _pin_locked_until = time.monotonic() + PIN_LOCKOUT_SECONDS
    raise HTTPException(status_code=401, detail="Wrong PIN")


def require_pin(
    pin: Optional[str] = Header(None, alias=PIN_HEADER),
    credentials: Optional[HTTPBasicCredentials] = Depends(optional_basic_auth),
):
    """Allow checklist actions with the right PIN, or with the admin login."""
    password = os.environ.get("ICPPV_ADMIN_PASSWORD")
    if credentials is not None and password and _admin_ok(credentials, password):
        return
    if pin is None:
        _configured_pin()  # report a missing server PIN before asking for one
        raise HTTPException(status_code=401, detail="PIN required")
    _check_pin(pin)


class PinCheck(BaseModel):
    pin: str


@app.post("/pin", status_code=204, include_in_schema=False)
def verify_pin(payload: PinCheck):
    """Let the checklist page check a PIN before remembering it (204 if right)."""
    _check_pin(payload.pin)
    return Response(status_code=204)


@app.get("/", include_in_schema=False)
def checklist_ui():
    return FileResponse(CHECKLIST_HTML)


@app.get("/icon.svg", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
def icon():
    return FileResponse(ICON_SVG, media_type="image/svg+xml")


# Home-screen icons for phones (iOS requests /apple-touch-icon.png on its own).
@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/icon-192.png", include_in_schema=False)
@app.get("/icon-512.png", include_in_schema=False)
def png_icon(request: Request):
    return FileResponse(STATIC_DIR / request.url.path.lstrip("/"), media_type="image/png")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/checklist", include_in_schema=False)
def old_checklist_url():
    return RedirectResponse("/")


@app.get("/admin", include_in_schema=False, dependencies=[Depends(require_admin)])
def admin_ui():
    return FileResponse(ADMIN_HTML)


@app.get("/items", response_model=List[ItemResponse])
def list_items(
    type: Optional[str] = None,
    group: Optional[str] = None,
    active: Optional[bool] = None,
    activated: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ChecklistItem)
    if type is not None:
        q = q.filter(ChecklistItem.type == type)
    if group is not None:
        q = q.filter(ChecklistItem.group == group)
    if active is not None:
        q = q.filter(ChecklistItem.active == active)
    if activated is not None:
        q = q.filter(ChecklistItem.activated == activated)
    return q.order_by(
        ChecklistItem.time.is_(None),
        ChecklistItem.time,
        ChecklistItem.sequence.is_(None),
        ChecklistItem.sequence,
        ChecklistItem.id,
    ).all()


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post(
    "/items", response_model=ItemResponse, status_code=201, dependencies=[Depends(require_admin)]
)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = ChecklistItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.post("/items/reset", dependencies=[Depends(require_admin)])
def reset_items(type: Optional[str] = None, db: Session = Depends(get_db)):
    """Mark every item as not done (activated = false) and drop snoozes, optionally only for one type."""
    q = db.query(ChecklistItem).filter(
        or_(ChecklistItem.activated.is_(True), ChecklistItem.snooze != 0)
    )
    if type is not None:
        q = q.filter(ChecklistItem.type == type)
    reset = q.update(
        {ChecklistItem.activated: False, ChecklistItem.snooze: 0}, synchronize_session=False
    )
    db.commit()
    return {"reset": reset}


@app.put("/items/{item_id}", response_model=ItemResponse, dependencies=[Depends(require_admin)])
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@app.put("/items/{item_id}/activated", response_model=ItemResponse, dependencies=[Depends(require_pin)])
def set_activated(item_id: int, payload: ActivatedUpdate, db: Session = Depends(get_db)):
    """Mark an item done / not done. Needs the checklist PIN (or the admin login), not an account."""
    item = db.get(ChecklistItem, item_id)
    # Inactive items are not part of the checklist, so they can't be ticked either.
    if item is None or not item.active:
        raise HTTPException(status_code=404, detail="Item not found")
    item.activated = payload.activated
    db.commit()
    db.refresh(item)
    return item


@app.put("/items/{item_id}/snooze", response_model=ItemResponse, dependencies=[Depends(require_pin)])
def set_snooze(item_id: int, payload: SnoozeUpdate, db: Session = Depends(get_db)):
    """Postpone an item by some minutes past its stored time. Needs the PIN, like set_activated."""
    item = db.get(ChecklistItem, item_id)
    if item is None or not item.active:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.time is None and payload.snooze:
        raise HTTPException(status_code=422, detail="Item has no time to snooze")
    item.snooze = payload.snooze
    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
