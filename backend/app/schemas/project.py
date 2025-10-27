from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProjectBase(BaseModel):
    projectName: str


class ProjectCreate(ProjectBase):
    tagIds: Optional[List[int]] = None


class ProjectUpdate(BaseModel):
    projectName: Optional[str] = None
    tagIds: Optional[List[int]] = None


class ProjectRead(ProjectBase):
    projectId: int
    tagIds: Optional[List[int]] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class UserProjectBase(BaseModel):
    userId: int
    projectId: int


class UserProjectCreate(UserProjectBase):
    pass


class UserProjectRead(UserProjectBase):
    userProjectId: int
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True
