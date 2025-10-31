from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, validator

from app.utils.roles import deserialize_roles


class UserBase(BaseModel):
    username: str
    roles: List[str] = Field(default_factory=lambda: ["researcher"])
    realName: Optional[str] = None

    @validator("roles", pre=True, allow_reuse=True)
    def ensure_roles(cls, value):
        if value is None:
            return ["researcher"]
        if isinstance(value, list):
            cleaned = [str(role) for role in value]
            return cleaned or ["researcher"]
        roles = deserialize_roles(value)
        return roles or ["researcher"]


class UserCreate(UserBase):
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    roles: Optional[List[str]] = None
    realName: Optional[str] = None

    @validator("roles", pre=True, allow_reuse=True)
    def ensure_roles(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            return [str(role) for role in value]
        roles = deserialize_roles(value)
        return roles or None


class UserRead(UserBase):
    userId: int
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)

class UserInfo(UserBase):
    userId: int
    username: str
    roles: List[str]
    realName: str | None = None