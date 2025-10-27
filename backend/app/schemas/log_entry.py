from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class LogEntryBase(BaseModel):
    action: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    userId: Optional[int] = None


class LogEntryCreate(LogEntryBase):
    pass


class LogEntryRead(LogEntryBase):
    logId: int
    createdAt: datetime

    class Config:
        orm_mode = True
