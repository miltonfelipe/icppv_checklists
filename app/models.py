import re
from datetime import time as TimeOfDay
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, PlainSerializer
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
    # Minutes the item is postponed past its time by users of the checklist; cleared by reset.
    snooze = Column(Integer, default=0, server_default=text("0"), nullable=False)


_HHMM = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)")


def _parse_hhmm(value):
    if isinstance(value, TimeOfDay):
        return value
    match = _HHMM.fullmatch(str(value).strip())
    if match is None:
        raise ValueError("time must be HH:MM in 24-hour format (00:00 to 23:59)")
    return TimeOfDay(int(match[1]), int(match[2]))


# Time of day in 24-hour "HH:MM", both in requests and responses.
Clock = Annotated[
    TimeOfDay,
    BeforeValidator(_parse_hhmm),
    PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str, when_used="json"),
]


class ItemCreate(BaseModel):
    type: str
    group: str
    description: str
    active: bool = True
    activated: bool = False
    time: Optional[Clock] = None
    sequence: Optional[int] = None


class ItemUpdate(BaseModel):
    type: Optional[str] = None
    group: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    activated: Optional[bool] = None
    time: Optional[Clock] = None
    sequence: Optional[int] = None


class ActivatedUpdate(BaseModel):
    activated: bool


class SnoozeUpdate(BaseModel):
    # Minutes after the stored time; 0 removes the snooze.
    snooze: int = Field(ge=0, le=24 * 60)


class ItemResponse(BaseModel):
    id: int
    type: str
    group: str
    description: str
    active: bool
    activated: bool
    time: Optional[Clock]
    sequence: Optional[int]
    snooze: int

    model_config = {"from_attributes": True}
