from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Subject
from app.schemas.subject import SubjectCreate, SubjectUpdate


def list_subjects(db: Session, skip: int = 0, limit: int = 100) -> List[Subject]:
    return (
        db.query(Subject)
        .order_by(Subject.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_subject(db: Session, subject_id: int) -> Optional[Subject]:
    return db.query(Subject).filter(Subject.subjectId == subject_id).first()


def create_subject(db: Session, subject_in: SubjectCreate) -> Subject:
    subject = Subject(
        subjectName=subject_in.subjectName,
        tagIds=subject_in.tagIds
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def update_subject(db: Session, subject: Subject, subject_in: SubjectUpdate) -> Subject:
    """更新受试者，只更新提供的字段"""
    update_data = subject_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subject, field, value)
    subject.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(subject)
    return subject


def delete_subject(db: Session, subject: Subject) -> None:
    db.delete(subject)
    db.commit()
