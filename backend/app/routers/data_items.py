from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.data_item import DataItemCreate, DataItemRead, DataItemUpdate
from app.services import data_item_service

router = APIRouter(
    prefix="/data-items",
    tags=["data-items"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[DataItemRead])
def list_data_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    project_id: Optional[int] = Query(None, alias="projectId"),
    subject_id: Optional[int] = Query(None, alias="subjectId"),
    user_id: Optional[int] = Query(None, alias="userId"),
    db: Session = Depends(get_db),
):
    data_items = data_item_service.list_data_items(
        db,
        skip=skip,
        limit=limit,
        project_id=project_id,
        subject_id=subject_id,
        user_id=user_id,
    )
    return data_items


@router.get("/{data_item_id}", response_model=DataItemRead)
def get_data_item(data_item_id: int, db: Session = Depends(get_db)):
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    return data_item


@router.post("/", response_model=DataItemRead, status_code=201)
def create_data_item(data_item_in: DataItemCreate, db: Session = Depends(get_db)):
    try:
        data_item = data_item_service.create_data_item(db, data_item_in)
        return data_item
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid foreign key reference")


@router.put("/{data_item_id}", response_model=DataItemRead)
def update_data_item(
    data_item_id: int,
    data_item_in: DataItemUpdate,
    db: Session = Depends(get_db),
):
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    try:
        updated = data_item_service.update_data_item(db, data_item, data_item_in)
        return updated
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid foreign key reference")


@router.delete("/{data_item_id}", status_code=200)
def delete_data_item(data_item_id: int, db: Session = Depends(get_db)):
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    data_item_service.delete_data_item(db, data_item)
    return None
