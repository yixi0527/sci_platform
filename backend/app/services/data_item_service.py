from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import DataItem
from app.schemas.data_item import DataItemCreate, DataItemUpdate


def list_data_items(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> List[DataItem]:
    query = db.query(DataItem)
    if project_id is not None:
        query = query.filter(DataItem.projectId == project_id)
    if subject_id is not None:
        query = query.filter(DataItem.subjectId == subject_id)
    if user_id is not None:
        query = query.filter(DataItem.userId == user_id)
    return (
        query.order_by(DataItem.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_data_item(db: Session, data_item_id: int) -> Optional[DataItem]:
    return db.query(DataItem).filter(DataItem.dataItemId == data_item_id).first()


def create_data_item(db: Session, data_item_in: DataItemCreate) -> DataItem:
    data_item = DataItem(**data_item_in.dict())
    db.add(data_item)
    db.commit()
    db.refresh(data_item)
    return data_item


def update_data_item(db: Session, data_item: DataItem, data_item_in: DataItemUpdate) -> DataItem:
    update_data = data_item_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(data_item, field, value)
    data_item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(data_item)
    return data_item


def delete_data_item(db: Session, data_item: DataItem) -> None:
    db.delete(data_item)
    db.commit()
