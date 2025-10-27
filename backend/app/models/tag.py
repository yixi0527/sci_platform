from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class EntityType(str, PyEnum):
    """实体类型枚举"""
    PROJECT = "PROJECT"
    SUBJECT = "SUBJECT"
    USER = "USER"
    DATAITEM = "DATAITEM"


class Tag(Base):
    __tablename__ = "Tag"
    __table_args__ = (
        UniqueConstraint('tagName', 'entityType', 'userId', name='uk_tag_name_entity_user'),
    )

    tagId = Column(Integer, primary_key=True, index=True)
    tagName = Column(String(100), nullable=False)
    tagDescription = Column(String(255))
    entityType = Column(
        Enum(EntityType, name="entity_type_enum", native_enum=False), 
        nullable=False,
        comment='标签所属实体类型'
    )
    userId = Column(
        Integer, 
        ForeignKey("User.userId", ondelete="SET NULL"),
        comment='创建该标签的用户ID'
    )
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now())

    # 关系
    creator = relationship("User", back_populates="tags")
