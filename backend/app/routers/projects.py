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

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[ProjectRead])
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    projects = project_service.list_projects(db, skip=skip, limit=limit)
    return projects


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=ProjectRead, status_code=201)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    try:
        project = project_service.create_project(db, project_in)
        return project
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Project name already exists")


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        updated = project_service.update_project(db, project, project_in)
        return updated
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Project name already exists")


@router.delete("/{project_id}", status_code=200)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project_service.delete_project(db, project)
    return None


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


@router.delete("/{project_id}/members/{user_id}", status_code=200)
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db)):
    membership = project_service.get_membership_by_keys(db, user_id=user_id, project_id=project_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    project_service.remove_user_from_project(db, membership)
    return None
