from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.log_entry import LogEntryCreate, LogEntryRead
from app.services import log_entry_service

router = APIRouter(
    prefix="/log-entries",
    tags=["log-entries"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[LogEntryRead])
def list_log_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None, alias="userId"),
    db: Session = Depends(get_db),
):
    return log_entry_service.list_log_entries(db, skip=skip, limit=limit, user_id=user_id)


@router.get("/{log_id}", response_model=LogEntryRead)
def get_log_entry(log_id: int, db: Session = Depends(get_db)):
    log = log_entry_service.get_log_entry(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="LogEntry not found")
    return log


@router.post("/", response_model=LogEntryRead, status_code=201)
def create_log_entry(log_in: LogEntryCreate, db: Session = Depends(get_db)):
    return log_entry_service.create_log_entry(db, log_in)


@router.delete("/{log_id}", status_code=200)
def delete_log_entry(log_id: int, db: Session = Depends(get_db)):
    log = log_entry_service.get_log_entry(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="LogEntry not found")
    log_entry_service.delete_log_entry(db, log)
    return None
