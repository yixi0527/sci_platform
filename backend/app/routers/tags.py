from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.models.tag import EntityType
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services import tag_service
from app.utils.roles import is_admin_or_tutor

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=List[TagRead])
def list_tags(
    entity_type: Optional[str] = Query(None, alias="entityType", description="Filter by entity type: Project, Subject, DataItem, User"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db),
):
    """获取标签列表
    
    权限规则：
    - admin/tutor: 看到所有标签
    - 其他用户: 只看到自己创建的标签
    """
    entity_type_enum = None
    if entity_type:
        try:
            entity_type_enum = EntityType(entity_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid entity type. Must be one of: Project, Subject, DataItem, User"
            )
    
    tags = tag_service.list_tags(db, current_user, entity_type_enum, skip, limit)
    
    # 返回标签列表
    return tags


@router.get("/{tag_id}", response_model=TagRead)
def get_tag(
    tag_id: int, 
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db)
):
    """获取标签详情
    
    权限规则：普通用户只能查看自己的标签
    """
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # 权限检查：普通用户只能查看自己的标签
    if not is_admin_or_tutor(current_user) and tag.userId != current_user.get('userId'):
        raise HTTPException(status_code=403, detail="Not authorized to view this tag")
    
    return tag


@router.get("/{tag_id}/usage")
def get_tag_usage(
    tag_id: int, 
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db)
):
    """获取标签使用统计"""
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # 权限检查
    if not is_admin_or_tutor(current_user) and tag.userId != current_user.get('userId'):
        raise HTTPException(status_code=403, detail="Not authorized to view this tag")
    
    stats = tag_service.get_tag_usage_stats(db, tag_id)
    return {
        "tagId": tag_id,
        "tagName": tag.tagName,
        "entityType": tag.entityType.value,
        "usage": stats,
    }


@router.post("/", response_model=TagRead, status_code=201)
def create_tag(
    tag_in: TagCreate, 
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db)
):
    """创建标签，自动关联当前用户"""
    try:
        # 检查是否已存在同名标签（同一用户、同一实体类型）
        existing = tag_service.get_tag_by_name(
            db, 
            tag_in.tagName, 
            tag_in.entityType,
            current_user.get('userId')
        )
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Tag '{tag_in.tagName}' already exists for {tag_in.entityType.value}"
            )
        
        tag = tag_service.create_tag(db, tag_in, current_user.get('userId'))
        return tag
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tag already exists")


@router.put("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: int, 
    tag_in: TagUpdate, 
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db)
):
    """更新标签（只能修改自己创建的标签）"""
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # 权限检查：只能修改自己创建的标签（或 admin/tutor 可以修改所有）
    if not is_admin_or_tutor(current_user) and tag.userId != current_user.get('userId'):
        raise HTTPException(status_code=403, detail="Not authorized to modify this tag")
    
    # 检查是否存在同名标签
    if tag_in.tagName:
        existing = tag_service.get_tag_by_name(
            db, 
            tag_in.tagName, 
            tag.entityType,
            tag.userId
        )
        if existing and existing.tagId != tag_id:
            raise HTTPException(
                status_code=400,
                detail=f"Tag '{tag_in.tagName}' already exists"
            )
    
    updated_tag = tag_service.update_tag(db, tag, tag_in)
    return updated_tag


@router.delete("/{tag_id}", status_code=200)
def delete_tag(
    tag_id: int, 
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db)
):
    """删除标签（只能删除自己创建的标签）"""
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # 权限检查：只能删除自己创建的标签（或 admin/tutor 可以删除所有）
    if not is_admin_or_tutor(current_user) and tag.userId != current_user.get('userId'):
        raise HTTPException(status_code=403, detail="Not authorized to delete this tag")
    
    tag_service.delete_tag(db, tag)
    return {"message": "Tag deleted successfully"}
