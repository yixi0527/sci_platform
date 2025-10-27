from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, JSON, func
from sqlalchemy.orm import relationship

from app.database import Base


class Project(Base):
    __tablename__ = "Project"

    projectId = Column(Integer, primary_key=True, index=True)
    projectName = Column(String(255), unique=True, nullable=False)
    tagIds = Column(JSON, comment='关联的标签ID列表')
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now())

    memberships = relationship(
        "UserProject",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    users = relationship(
        "User",
        secondary="UserProject",
        back_populates="projects",
        viewonly=True,
    )
    data_items = relationship("DataItem", back_populates="project")


class UserProject(Base):
    __tablename__ = "UserProject"
    __table_args__ = (UniqueConstraint("userId", "projectId", name="uq_user_project"),)

    userProjectId = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("User.userId", ondelete="CASCADE"), nullable=False)
    projectId = Column(Integer, ForeignKey("Project.projectId", ondelete="CASCADE"), nullable=False)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="memberships")
    project = relationship("Project", back_populates="memberships")
