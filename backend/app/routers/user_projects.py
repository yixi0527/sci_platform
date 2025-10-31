"""
User-Project association router for managing project memberships.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.project import UserProjectCreate, UserProjectRead
from app.services import project_service

router = APIRouter(
    prefix="/user-projects",
    tags=["user-projects"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[UserProjectRead])
def list_user_projects(
    project_ids: Optional[str] = Query(None, alias="project_ids"),
    user_id: Optional[int] = Query(None, alias="userId"),
    project_id: Optional[int] = Query(None, alias="projectId"),
    db: Session = Depends(get_db),
):
    """
    List user-project associations with optional filters.
    
    - project_ids: Comma-separated list of project IDs
    - user_id: Filter by user ID
    - project_id: Filter by project ID
    """
    # If project_ids is provided, parse it and return all matching memberships
    if project_ids:
        try:
            id_list = [int(x.strip()) for x in project_ids.split(',') if x.strip()]
            all_memberships = []
            for pid in id_list:
                memberships = project_service.list_memberships(db, project_id=pid)
                all_memberships.extend(memberships)
            return all_memberships
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_ids format")
    
    # Otherwise use the filter parameters
    return project_service.list_memberships(db, project_id=project_id, user_id=user_id)


@router.get("/user/{user_id}", response_model=List[UserProjectRead])
def list_user_projects_by_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all projects for a specific user.
    """
    return project_service.list_memberships(db, user_id=user_id)


@router.post("/", response_model=UserProjectRead, status_code=201)
def create_user_project(
    membership_in: UserProjectCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new user-project association.
    """
    try:
        return project_service.add_user_to_project(db, membership_in)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{user_project_id}", status_code=204)
def delete_user_project(
    user_project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    删除用户-项目关联
    
    Args:
        user_project_id: 关联ID
        
    Returns:
        204 No Content
        
    Raises:
        404: 关联不存在
    """
    membership = project_service.get_membership(db, user_project_id)
    if not membership:
        raise HTTPException(status_code=404, detail="User-project association not found")
    project_service.remove_user_from_project(db, membership)
