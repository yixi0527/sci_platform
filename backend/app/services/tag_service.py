from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Tag, Project, Subject, DataItem
from app.models.tag import EntityType
from app.schemas.tag import TagCreate, TagUpdate
from app.utils.roles import is_admin_or_tutor


def list_tags(
    db: Session, 
    current_user: dict,
    entity_type: Optional[EntityType] = None,
    skip: int = 0, 
    limit: int = 100
):
    """获取标签列表
    
    权限规则：
    - admin/tutor: 看到所有标签
    - 其他用户: 只看到自己创建的标签
    """
    query = db.query(Tag)
    
    # 权限过滤
    if not is_admin_or_tutor(current_user):
        query = query.filter(Tag.userId == current_user.get('userId'))
    
    # 实体类型过滤
    if entity_type:
        query = query.filter(Tag.entityType == entity_type)
    
    return (
        query
        .order_by(Tag.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_tag(db: Session, tag_id: int):
    return db.query(Tag).filter(Tag.tagId == tag_id).first()


def get_tag_by_name(
    db: Session, 
    tag_name: str, 
    entity_type: EntityType,
    user_id: int
):
    """根据标签名称、实体类型和用户ID查找标签"""
    return (
        db.query(Tag)
        .filter(
            Tag.tagName == tag_name,
            Tag.entityType == entity_type,
            Tag.userId == user_id
        )
        .first()
    )


def get_tag_usage_stats(db: Session, tag_id: int):
    """获取标签使用统计
    
    统计在各个实体中使用该标签的次数
    """
    tag = get_tag(db, tag_id)
    if not tag:
        return {"count": 0}
    
    # 根据实体类型统计使用次数
    entity_type = tag.entityType
    count = 0
    
    if entity_type == EntityType.PROJECT:
        count = db.query(Project).filter(
            Project.tagIds.contains([tag_id])
        ).count()
    elif entity_type == EntityType.SUBJECT:
        count = db.query(Subject).filter(
            Subject.tagIds.contains([tag_id])
        ).count()
    elif entity_type == EntityType.DATAITEM:
        count = db.query(DataItem).filter(
            DataItem.tagIds.contains([tag_id])
        ).count()
    
    return {"count": count}


def create_tag(db: Session, tag_in: TagCreate, user_id: int):
    tag = Tag(
        tagName=tag_in.tagName,
        tagDescription=tag_in.tagDescription,
        entityType=tag_in.entityType,
        userId=user_id,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag: Tag, tag_in: TagUpdate):
    update_data = tag_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)
    
    # 显式更新 updatedAt
    tag.updatedAt = datetime.utcnow()
    
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag: Tag) -> None:
    db.delete(tag)
    db.commit()
