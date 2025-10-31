"""统一的错误处理工具"""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def handle_integrity_error(e: IntegrityError, entity_name: str = "资源") -> None:
    """
    统一处理数据库唯一性约束错误
    
    Args:
        e: IntegrityError 异常
        entity_name: 实体名称（用于错误消息）
        
    Raises:
        HTTPException: 包含友好错误消息的 400 异常
    """
    raw = ""
    try:
        # 尝试获取原始错误信息
        if hasattr(e, "orig") and e.orig is not None:
            raw = str(e.orig)
        else:
            raw = str(e)
    except Exception:
        raw = str(e)
    
    lower = raw.lower()
    
    # 根据错误信息生成友好的错误消息
    if "username" in lower or "unique_username" in lower:
        detail = "用户名已存在"
    elif "projectname" in lower or "project_name" in lower or "unique_projectname" in lower:
        detail = "项目名称已存在"
    elif "realname" in lower or "real_name" in lower:
        detail = "真实姓名已存在，为避免管理混乱，重名情况请作区分"
    elif "subjectname" in lower or "subject_name" in lower:
        detail = "受试者名称已存在"
    elif "tagname" in lower or "tag_name" in lower:
        detail = "标签名称已存在"
    elif "duplicate" in lower or "unique" in lower:
        detail = f"{entity_name}已存在或违反唯一性约束"
    elif "foreign key" in lower:
        detail = "关联的数据不存在，请检查关联ID是否正确"
    else:
        detail = f"数据库错误: {raw}"
    
    raise HTTPException(status_code=400, detail=detail)


def handle_not_found(entity_name: str, entity_id: int | str) -> None:
    """
    统一处理资源未找到错误
    
    Args:
        entity_name: 实体名称
        entity_id: 实体ID
        
    Raises:
        HTTPException: 404 异常
    """
    raise HTTPException(
        status_code=404,
        detail=f"{entity_name} (ID: {entity_id}) 未找到"
    )


def handle_permission_denied(action: str = "执行此操作") -> None:
    """
    统一处理权限不足错误
    
    Args:
        action: 操作描述
        
    Raises:
        HTTPException: 403 异常
    """
    raise HTTPException(
        status_code=403,
        detail=f"您没有权限{action}"
    )
