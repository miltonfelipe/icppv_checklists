from datetime import time as TimeOfDay
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String, Time, text

from app.database import Base


class ChecklistItem(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    type = Column(String, nullable=False)
    group = Column("group", String, nullable=False)
    description = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    activated = Column(Boolean, default=False, server_default=text("0"), nullable=False)
    # Time of day the task must be performed (no date); optional.
    time = Column(Time, nullable=True)
    # Position of the item in its checklist; items without one come last.
    sequence = Column(Integer, nullable=True)


class ItemCreate(BaseModel):
    type: str
    group: str
    description: str
    active: bool = True
    activated: bool = False
    time: Optional[TimeOfDay] = None
    sequence: Optional[int] = None


class ItemUpdate(BaseModel):
    type: Optional[str] = None
    group: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    activated: Optional[bool] = None
    time: Optional[TimeOfDay] = None
    sequence: Optional[int] = None


class ItemResponse(BaseModel):
    id: int
    type: str
    group: str
    description: str
    active: bool
    activated: bool
    time: Optional[TimeOfDay]
    sequence: Optional[int]

    model_config = {"from_attributes": True}
