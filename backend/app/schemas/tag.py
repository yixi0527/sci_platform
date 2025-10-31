from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.tag import EntityType


class TagBase(BaseModel):
    tagName: str
    tagDescription: Optional[str] = None


class TagCreate(TagBase):
    entityType: EntityType
    # userId will be set from current_user in the route


class TagUpdate(BaseModel):
    tagName: Optional[str] = None
    tagDescription: Optional[str] = None
    # entityType is immutable after creation


class TagRead(TagBase):
    tagId: int
    entityType: EntityType
    userId: Optional[int] = None
    creatorName: Optional[str] = None  # 创建者用户名
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)
