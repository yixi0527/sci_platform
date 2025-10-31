from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.log_entry import LogEntryCreate, LogEntryRead
from app.services import log_entry_service
from app.utils.roles import is_admin_or_tutor

router = APIRouter(
    prefix="/log-entries",
    tags=["log-entries"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/", response_model=Dict[str, Any])
def list_log_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None, alias="userId"),
    action_type: Optional[str] = Query(None, alias="actionType"),
    action: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None, alias="startTime"),
    end_time: Optional[datetime] = Query(None, alias="endTime"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    查询日志列表
    - admin和tutor可以查看所有日志
    - 普通用户只能查看自己的日志
    - 支持按操作类型、具体操作、时间范围过滤
    """
    # 权限控制：非admin/tutor只能查询自己的日志
    if not is_admin_or_tutor(current_user):
        user_id = current_user.get('userId')
    
    records, total = log_entry_service.list_log_entries(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        action_type=action_type,
        action=action,
        start_time=start_time,
        end_time=end_time,
    )
    
    # 装饰数据，添加用户名
    items = []
    for log in records:
        log_dict = {
            "logId": log.logId,
            "userId": log.userId,
            "action": log.action,
            "actionType": log.actionType,
            "detail": log.detail,
            "createdAt": log.createdAt,
            "username": log.user.username if log.user else None,
        }
        items.append(log_dict)
    
    return {"items": items, "total": total}


@router.get("/action-types", response_model=List[str])
def get_action_types(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """获取所有操作类型（用于前端下拉选择）"""
    return log_entry_service.get_action_types(db)


@router.get("/{log_id}", response_model=LogEntryRead)
def get_log_entry(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """获取单条日志详情"""
    log = log_entry_service.get_log_entry(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="LogEntry not found")
    
    # 权限控制：非admin/tutor只能查看自己的日志
    if not is_admin_or_tutor(current_user):
        if log.userId != current_user.get('userId'):
            raise HTTPException(status_code=403, detail="Permission denied")
    
    return log


@router.post("/", response_model=LogEntryRead, status_code=201)
def create_log_entry(
    log_in: LogEntryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """创建日志条目（通常由系统自动调用）"""
    return log_entry_service.create_log_entry(db, log_in)


@router.delete("/{log_id}", status_code=200)
def delete_log_entry(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """删除日志条目（仅admin）"""
    if not is_admin_or_tutor(current_user):
        raise HTTPException(status_code=403, detail="Permission denied: admin or tutor required")
    
    log = log_entry_service.get_log_entry(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="LogEntry not found")
    log_entry_service.delete_log_entry(db, log)
    return log


@router.delete("/{log_id}", status_code=204)
def delete_log_entry(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    删除日志（仅管理员）
    
    Args:
        log_id: 日志ID
        
    Returns:
        204 No Content
        
    Raises:
        404: 日志不存在
        403: 权限不足（仅管理员可删除）
    """
    if not is_admin_or_tutor(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    log = log_entry_service.get_log_entry(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="LogEntry not found")
    
    log_entry_service.delete_log_entry(db, log)
