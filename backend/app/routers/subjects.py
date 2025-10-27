from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.subject import SubjectCreate, SubjectRead, SubjectUpdate
from app.services import subject_service

router = APIRouter(
    prefix="/subjects",
    tags=["subjects"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[SubjectRead])
def list_subjects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    subjects = subject_service.list_subjects(db, skip=skip, limit=limit)
    return subjects


@router.get("/{subject_id}", response_model=SubjectRead)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.post("/", response_model=SubjectRead, status_code=201)
def create_subject(subject_in: SubjectCreate, db: Session = Depends(get_db)):
    try:
        subject = subject_service.create_subject(db, subject_in)
        return subject
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Subject already exists")


@router.put("/{subject_id}", response_model=SubjectRead)
def update_subject(subject_id: int, subject_in: SubjectUpdate, db: Session = Depends(get_db)):
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    updated = subject_service.update_subject(db, subject, subject_in)
    return updated


@router.delete("/{subject_id}", status_code=200)
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    subject_service.delete_subject(db, subject)
    return None
