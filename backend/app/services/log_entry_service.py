from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import LogEntry, User
from app.schemas.log_entry import LogEntryCreate


def list_log_entries(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
    action: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Tuple[List[LogEntry], int]:
    """
    查询日志列表，返回记录和总数
    
    Args:
        db: 数据库会话
        skip: 跳过记录数
        limit: 返回记录数
        user_id: 按用户ID过滤
        action_type: 按操作类型过滤
        action: 按具体操作过滤
        start_time: 开始时间
        end_time: 结束时间
    
    Returns:
        (记录列表, 总记录数)
    """
    query = db.query(LogEntry)
    
    # 应用过滤条件
    if user_id is not None:
        query = query.filter(LogEntry.userId == user_id)
    if action_type:
        query = query.filter(LogEntry.actionType == action_type)
    if action:
        query = query.filter(LogEntry.action.like(f"%{action}%"))
    if start_time:
        query = query.filter(LogEntry.createdAt >= start_time)
    if end_time:
        query = query.filter(LogEntry.createdAt <= end_time)
    
    # 获取总数
    total = query.count()
    
    # 获取分页数据
    records = (
        query.order_by(LogEntry.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return records, total


def get_log_entry(db: Session, log_id: int) -> Optional[LogEntry]:
    """根据ID获取日志条目"""
    return db.query(LogEntry).filter(LogEntry.logId == log_id).first()


def create_log_entry(db: Session, log_in: LogEntryCreate) -> LogEntry:
    """创建日志条目"""
    log = LogEntry(
        userId=log_in.userId,
        action=log_in.action,
        actionType=log_in.actionType,
        detail=log_in.detail,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def delete_log_entry(db: Session, log: LogEntry) -> None:
    """删除日志条目"""
    db.delete(log)
    db.commit()


def get_action_types(db: Session) -> List[str]:
    """获取所有不重复的操作类型"""
    result = db.query(LogEntry.actionType).distinct().filter(LogEntry.actionType.isnot(None)).all()
    return [r[0] for r in result if r[0]]
