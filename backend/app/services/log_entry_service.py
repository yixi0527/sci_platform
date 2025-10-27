from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import LogEntry
from app.schemas.log_entry import LogEntryCreate


def list_log_entries(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
) -> List[LogEntry]:
    query = db.query(LogEntry)
    if user_id is not None:
        query = query.filter(LogEntry.userId == user_id)
    return (
        query.order_by(LogEntry.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_log_entry(db: Session, log_id: int) -> Optional[LogEntry]:
    return db.query(LogEntry).filter(LogEntry.logId == log_id).first()


def create_log_entry(db: Session, log_in: LogEntryCreate) -> LogEntry:
    log = LogEntry(
        userId=log_in.userId,
        action=log_in.action,
        detail=log_in.detail,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def delete_log_entry(db: Session, log: LogEntry) -> None:
    db.delete(log)
    db.commit()
