from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Project, UserProject
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate, UserProjectCreate


def list_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    return (
        db.query(Project)
        .order_by(Project.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project(db: Session, project_id: int) -> Optional[Project]:
    return db.query(Project).filter(Project.projectId == project_id).first()


def create_project(db: Session, project_in: ProjectCreate) -> Project:
    project = Project(
        projectName=project_in.projectName,
        tagIds=project_in.tagIds
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    """更新项目，只更新提供的字段"""
    update_data = project_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    project.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()


def list_memberships(db: Session, project_id: Optional[int] = None, user_id: Optional[int] = None) -> List[UserProject]:
    query = db.query(UserProject)
    if project_id is not None:
        query = query.filter(UserProject.projectId == project_id)
    if user_id is not None:
        query = query.filter(UserProject.userId == user_id)
    return query.all()


def get_membership(db: Session, membership_id: int) -> Optional[UserProject]:
    return db.query(UserProject).filter(UserProject.userProjectId == membership_id).first()


def get_membership_by_keys(db: Session, user_id: int, project_id: int) -> Optional[UserProject]:
    return (
        db.query(UserProject)
        .filter(
            UserProject.userId == user_id,
            UserProject.projectId == project_id,
        )
        .first()
    )


def add_user_to_project(db: Session, membership_in: UserProjectCreate) -> UserProject:
    membership = get_membership_by_keys(
        db,
        user_id=membership_in.userId,
        project_id=membership_in.projectId,
    )
    if membership:
        return membership
    membership = UserProject(
        userId=membership_in.userId,
        projectId=membership_in.projectId,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def remove_user_from_project(db: Session, membership: UserProject) -> None:
    db.delete(membership)
    db.commit()
