"""
数据项管理路由
提供数据项的增删改查、按项目/受试者/用户筛选等接口
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.data_item import DataItemCreate, DataItemRead, DataItemUpdate
from app.services import data_item_service
from app.utils.logger import api_logger as logger
from app.utils.log_helper import log_data

router = APIRouter(
    prefix="/data-items",
    tags=["data-items"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[DataItemRead])
def list_data_items(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    project_id: Optional[int] = Query(None, alias="projectId", description="项目ID筛选"),
    subject_id: Optional[int] = Query(None, alias="subjectId", description="受试者ID筛选"),
    user_id: Optional[int] = Query(None, alias="userId", description="用户ID筛选"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    获取数据项列表（支持分页和多条件筛选）
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        project_id: 按项目ID筛选（可选）
        subject_id: 按受试者ID筛选（可选）
        user_id: 按用户ID筛选（可选）
        
    Returns:
        List[DataItemRead]: 数据项列表
    """
    logger.info(
        f"List data items requested by user: {current_user.get('username')}, "
        f"filters: project_id={project_id}, subject_id={subject_id}, user_id={user_id}"
    )
    data_items = data_item_service.list_data_items(
        db,
        skip=skip,
        limit=limit,
        project_id=project_id,
        subject_id=subject_id,
        user_id=user_id,
    )
    logger.debug(f"Found {len(data_items)} data items")
    return data_items


@router.get("/{data_item_id}", response_model=DataItemRead)
def get_data_item(data_item_id: int, db: Session = Depends(get_db)):
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    return data_item


@router.post("/", response_model=DataItemRead, status_code=201)
def create_data_item(
    data_item_in: DataItemCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    try:
        data_item = data_item_service.create_data_item(db, data_item_in)
        
        # 记录日志
        log_data(db, current_user.get('userId'), 'create_data_item', {
            'dataItemId': data_item.dataItemId,
            'name': data_item.name,
            'projectId': data_item.projectId,
            'subjectId': data_item.subjectId,
        })
        
        return data_item
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid foreign key reference")


@router.put("/{data_item_id}", response_model=DataItemRead)
def update_data_item(
    data_item_id: int,
    data_item_in: DataItemUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    try:
        updated = data_item_service.update_data_item(db, data_item, data_item_in)
        
        # 记录日志
        log_data(db, current_user.get('userId'), 'update_data_item', {
            'dataItemId': data_item_id,
            'name': updated.name,
            'changes': data_item_in.model_dump(exclude_unset=True),
        })
        
        return updated
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid foreign key reference")


@router.delete("/{data_item_id}", status_code=204)
def delete_data_item(
    data_item_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    删除数据项
    
    Args:
        data_item_id: 数据项ID
        
    Returns:
        204 No Content
        
    Raises:
        404: 数据项不存在
    """
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    
    name = data_item.name
    data_item_service.delete_data_item(db, data_item)
    
    # 记录日志
    log_data(db, current_user.get('userId'), 'delete_data_item', {
        'dataItemId': data_item_id,
        'name': name,
    })
