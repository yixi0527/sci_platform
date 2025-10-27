from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SubjectBase(BaseModel):
    subjectName: str


class SubjectCreate(SubjectBase):
    tagIds: Optional[List[int]] = None


class SubjectUpdate(BaseModel):
    subjectName: Optional[str] = None
    tagIds: Optional[List[int]] = None


class SubjectRead(SubjectBase):
    subjectId: int
    tagIds: Optional[List[int]] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True
