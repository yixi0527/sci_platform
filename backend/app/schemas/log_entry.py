from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class LogEntryBase(BaseModel):
    action: Optional[str] = None
    actionType: Optional[str] = None  # AUTH, PROJECT, USER, DATA, SUBJECT, TAG, FILE, ANALYSIS
    detail: Optional[Dict[str, Any]] = None
    userId: Optional[int] = None


class LogEntryCreate(LogEntryBase):
    pass


class LogEntryRead(LogEntryBase):
    logId: int
    createdAt: datetime
    username: Optional[str] = None  # 用户名，方便前端显示

    model_config = ConfigDict(from_attributes=True)


class LogEntryQuery(BaseModel):
    """日志查询参数"""
    skip: int = 0
    limit: int = 100
    userId: Optional[int] = None
    actionType: Optional[str] = None  # 按操作类型过滤
    action: Optional[str] = None  # 按具体操作过滤
    startTime: Optional[datetime] = None  # 开始时间
    endTime: Optional[datetime] = None  # 结束时间
