import os
import secrets
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import ActivatedUpdate, ChecklistItem, ItemCreate, ItemResponse, ItemUpdate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ICPPV Checklists API")

STATIC_DIR = Path(__file__).parent / "static"
ADMIN_HTML = STATIC_DIR / "admin.html"
CHECKLIST_HTML = STATIC_DIR / "checklist.html"

ADMIN_REALM = "ICPPV admin"
basic_auth = HTTPBasic(realm=ADMIN_REALM)


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
    user = os.environ.get("ICPPV_ADMIN_USER", "admin")
    user_ok = secrets.compare_digest(credentials.username.encode(), user.encode())
    password_ok = secrets.compare_digest(credentials.password.encode(), password.encode())
    if not (user_ok and password_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": f'Basic realm="{ADMIN_REALM}"'},
        )


@app.get("/", include_in_schema=False)
def checklist_ui():
    return FileResponse(CHECKLIST_HTML)


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
        ChecklistItem.sequence.is_(None), ChecklistItem.sequence, ChecklistItem.id
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
    """Mark every item as not done (activated = false), optionally only for one type."""
    q = db.query(ChecklistItem).filter(ChecklistItem.activated.is_(True))
    if type is not None:
        q = q.filter(ChecklistItem.type == type)
    reset = q.update({ChecklistItem.activated: False}, synchronize_session=False)
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


@app.put("/items/{item_id}/activated", response_model=ItemResponse)
def set_activated(item_id: int, payload: ActivatedUpdate, db: Session = Depends(get_db)):
    """Mark an item done / not done. Open (no login) so the checklist can be used by anyone."""
    item = db.get(ChecklistItem, item_id)
    # Inactive items are not part of the checklist, so they can't be ticked either.
    if item is None or not item.active:
        raise HTTPException(status_code=404, detail="Item not found")
    item.activated = payload.activated
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
