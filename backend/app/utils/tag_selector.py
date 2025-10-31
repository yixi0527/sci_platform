"""
基于标签筛选 data_item 的工具
- 支持 AND/OR 逻辑组合
- 仅返回 CSV 类型的数据项
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.data_item import DataItem
from app.models.tag import Tag


def select_by_tags(
    db: Session,
    project_id: int,
    tag_filter: dict,
    item_type: Optional[str] = None
) -> List[DataItem]:
    """
    根据标签筛选项目下的 data_items
    
    Args:
        db: 数据库会话
        project_id: 项目 ID
        tag_filter: 标签筛选条件，格式：
            {
                "and": [tag_id1, tag_id2, ...],  # 必须同时包含这些标签
                "or": [tag_id3, tag_id4, ...]     # 包含其中任一标签即可
            }
        item_type: 可选的数据项类型过滤（如 'fluorescence' 或 'label'）
    
    Returns:
        符合条件的 DataItem 列表
    """
    # 输入验证
    if not isinstance(tag_filter, dict):
        return []
    
    and_tags = tag_filter.get("and", [])
    or_tags = tag_filter.get("or", [])
    
    # 如果没有任何标签筛选条件，返回空列表（避免返回所有数据）
    if not and_tags and not or_tags:
        return []
    
    # 基础查询：项目下的所有数据项
    query = db.query(DataItem).filter(DataItem.projectId == project_id)
    
    # 类型过滤
    if item_type:
        query = query.filter(DataItem.type == item_type)
    
    # AND 标签筛选：数据项必须关联所有这些标签
    if and_tags:
        # 验证 tag_ids 是有效的整数列表
        valid_and_tags = [tid for tid in and_tags if isinstance(tid, int)]
        if not valid_and_tags:
            return []
        
        for tag_id in valid_and_tags:
            query = query.filter(DataItem.tags.any(Tag.id == tag_id))
    
    # OR 标签筛选：数据项关联任一标签即可
    if or_tags:
        # 验证 tag_ids 是有效的整数列表
        valid_or_tags = [tid for tid in or_tags if isinstance(tid, int)]
        if not valid_or_tags:
            return []
        
        query = query.filter(DataItem.tags.any(Tag.id.in_(valid_or_tags)))
    
    return query.all()


def get_data_items_by_ids(
    db: Session,
    project_id: int,
    data_item_ids: List[int]
) -> List[DataItem]:
    """
    根据 ID 列表获取项目下的 data_items
    
    Args:
        db: 数据库会话
        project_id: 项目 ID
        data_item_ids: data_item ID 列表
    
    Returns:
        DataItem 列表
    """
    return db.query(DataItem).filter(
        and_(
            DataItem.id.in_(data_item_ids),
            DataItem.projectId == project_id
        )
    ).all()
