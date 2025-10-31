"""
项目管理路由
提供项目的增删改查、成员管理等接口
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    UserProjectCreate,
    UserProjectRead,
)
from app.services import project_service
from app.utils.logger import api_logger as logger
from app.utils.log_helper import log_project

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[ProjectRead])
def list_projects(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    获取项目列表（支持分页）
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        
    Returns:
        List[ProjectRead]: 项目列表
    """
    logger.info(f"List projects requested by user: {current_user.get('username')}, skip={skip}, limit={limit}")
    projects = project_service.list_projects(db, skip=skip, limit=limit)
    logger.debug(f"Found {len(projects)} projects")
    return projects


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    获取项目详情
    
    Args:
        project_id: 项目ID
        
    Returns:
        ProjectRead: 项目详情
        
    Raises:
        404: 项目不存在
    """
    logger.info(f"Get project {project_id} requested by user: {current_user.get('username')}")
    project = project_service.get_project(db, project_id)
    if not project:
        logger.warning(f"Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=ProjectRead, status_code=201)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    创建新项目
    
    Args:
        project_in: 项目创建数据
        
    Returns:
        ProjectRead: 创建的项目
        
    Raises:
        400: 项目名称已存在
    """
    logger.info(f"Create project requested by user: {current_user.get('username')}, name: {project_in.projectName}")
    try:
        project = project_service.create_project(db, project_in)
        logger.info(f"Project created successfully: {project.projectId}")
        
        # 记录日志
        log_project(db, current_user.get('userId'), 'create_project', {
            'projectId': project.projectId,
            'projectName': project.projectName,
        })
        
        return project
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=400, detail="Project name already exists")


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, 
    project_in: ProjectUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        updated = project_service.update_project(db, project, project_in)
        
        # 记录日志
        log_project(db, current_user.get('userId'), 'update_project', {
            'projectId': project_id,
            'projectName': updated.projectName,
            'changes': project_in.model_dump(exclude_unset=True),
        })
        
        return updated
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Project name already exists")


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    删除项目
    
    Args:
        project_id: 项目ID
        
    Returns:
        204 No Content
        
    Raises:
        404: 项目不存在
    """
    logger.info(f"Delete project {project_id} requested by user: {current_user.get('username')}")
    project = project_service.get_project(db, project_id)
    if not project:
        logger.warning(f"Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_name = project.projectName
    project_service.delete_project(db, project)
    
    # 记录日志
    log_project(db, current_user.get('userId'), 'delete_project', {
        'projectId': project_id,
        'projectName': project_name,
    })
    
    logger.info(f"Project deleted: {project_id} ({project_name})")


@router.get("/{project_id}/members", response_model=List[UserProjectRead])
def list_project_members(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_service.list_memberships(db, project_id=project_id)


@router.post("/{project_id}/members", response_model=UserProjectRead, status_code=201)
def add_member(project_id: int, payload: UserProjectCreate, db: Session = Depends(get_db)):
    if payload.projectId != project_id:
        raise HTTPException(status_code=400, detail="projectId mismatch in payload")
    membership = project_service.add_user_to_project(db, payload)
    return membership


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: int, 
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    移除项目成员
    
    Args:
        project_id: 项目ID
        user_id: 用户ID
        
    Returns:
        204 No Content
        
    Raises:
        404: 成员关系不存在
    """
    logger.info(f"Remove user {user_id} from project {project_id} requested by user: {current_user.get('username')}")
    membership = project_service.get_membership_by_keys(db, user_id=user_id, project_id=project_id)
    if not membership:
        logger.warning(f"Membership not found: user {user_id} in project {project_id}")
        raise HTTPException(status_code=404, detail="Membership not found")
    project_service.remove_user_from_project(db, membership)
    logger.info(f"User {user_id} removed from project {project_id}")
