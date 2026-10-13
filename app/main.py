from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import ChecklistItem, ItemCreate, ItemResponse, ItemUpdate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ICPPV Checklists API")

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"
CHECKLIST_HTML = STATIC_DIR / "checklist.html"


@app.get("/", include_in_schema=False)
def web_ui():
    return FileResponse(INDEX_HTML)


@app.get("/checklist", include_in_schema=False)
def checklist_ui():
    return FileResponse(CHECKLIST_HTML)


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
    return q.all()


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = ChecklistItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
