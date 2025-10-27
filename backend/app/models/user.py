from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "User"

    userId = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    passwordHash = Column(String(255), nullable=False)
    roles = Column(String(500), nullable=False, default='["researcher"]')
    realName = Column(String(100))
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now())

    memberships = relationship(
        "UserProject",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    projects = relationship(
        "Project",
        secondary="UserProject",
        back_populates="users",
        viewonly=True,
    )
    data_items = relationship("DataItem", back_populates="owner")
    tags = relationship("Tag", back_populates="creator")
    logs = relationship("LogEntry", back_populates="user")
