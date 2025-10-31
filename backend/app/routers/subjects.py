"""
受试者管理路由
提供受试者的增删改查接口
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.subject import SubjectCreate, SubjectRead, SubjectUpdate
from app.services import subject_service
from app.utils.logger import api_logger as logger
from app.utils.error_handler import handle_integrity_error

router = APIRouter(
    prefix="/subjects",
    tags=["subjects"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[SubjectRead])
def list_subjects(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    获取受试者列表（支持分页）
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        
    Returns:
        List[SubjectRead]: 受试者列表
    """
    logger.info(f"List subjects requested by user: {current_user.get('username')}, skip={skip}, limit={limit}")
    subjects = subject_service.list_subjects(db, skip=skip, limit=limit)
    logger.debug(f"Found {len(subjects)} subjects")
    return subjects


@router.get("/{subject_id}", response_model=SubjectRead)
def get_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    获取受试者详情
    
    Args:
        subject_id: 受试者ID
        
    Returns:
        SubjectRead: 受试者详情
        
    Raises:
        404: 受试者不存在
    """
    logger.info(f"Get subject {subject_id} requested by user: {current_user.get('username')}")
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        logger.warning(f"Subject {subject_id} not found")
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.post("/", response_model=SubjectRead, status_code=201)
def create_subject(
    subject_in: SubjectCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    创建新受试者
    
    Args:
        subject_in: 受试者创建数据
        
    Returns:
        SubjectRead: 创建的受试者
        
    Raises:
        400: 受试者名称已存在
    """
    logger.info(f"Create subject requested by user: {current_user.get('username')}, name: {subject_in.subjectName}")
    try:
        subject = subject_service.create_subject(db, subject_in)
        logger.info(f"Subject created successfully: {subject.subjectId}")
        return subject
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create subject: {e}")
        handle_integrity_error(e, "受试者")


@router.put("/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: int, 
    subject_in: SubjectUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    更新受试者
    
    Args:
        subject_id: 受试者ID
        subject_in: 更新数据
        
    Returns:
        SubjectRead: 更新后的受试者
        
    Raises:
        404: 受试者不存在
        400: 受试者名称已存在
    """
    logger.info(f"Update subject {subject_id} requested by user: {current_user.get('username')}")
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        logger.warning(f"Subject {subject_id} not found")
        raise HTTPException(status_code=404, detail="Subject not found")
    
    try:
        updated = subject_service.update_subject(db, subject, subject_in)
        logger.info(f"Subject updated: {subject_id}")
        return updated
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to update subject {subject_id}: {e}")
        handle_integrity_error(e, "受试者")


@router.delete("/{subject_id}", status_code=204)
def delete_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    删除受试者
    
    Args:
        subject_id: 受试者ID
        
    Returns:
        204 No Content
        
    Raises:
        404: 受试者不存在
    """
    logger.info(f"Delete subject {subject_id} requested by user: {current_user.get('username')}")
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        logger.warning(f"Subject {subject_id} not found")
        raise HTTPException(status_code=404, detail="Subject not found")
    
    subject_name = subject.subjectName
    subject_service.delete_subject(db, subject)
    logger.info(f"Subject deleted: {subject_id} ({subject_name})")
