"""
日志记录辅助工具
提供便捷的日志记录函数，用于在各个路由中记录用户操作
"""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import LogEntry


# 操作类型常量
class ActionType:
    AUTH = "AUTH"  # 认证相关
    PROJECT = "PROJECT"  # 项目管理
    USER = "USER"  # 用户管理
    DATA = "DATA"  # 数据项管理
    SUBJECT = "SUBJECT"  # 受试者管理
    TAG = "TAG"  # 标签管理
    FILE = "FILE"  # 文件操作
    ANALYSIS = "ANALYSIS"  # 数据分析


def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    action_type: str,
    detail: Optional[Dict[str, Any]] = None,
) -> LogEntry:
    """
    记录用户操作日志
    
    Args:
        db: 数据库会话
        user_id: 用户ID（可为None，如系统操作）
        action: 具体操作名称，如 'create_project', 'delete_user'
        action_type: 操作类型，使用 ActionType 中的常量
        detail: 操作详情（JSON格式）
    
    Returns:
        创建的日志条目
    """
    log_entry = LogEntry(
        userId=user_id,
        action=action,
        actionType=action_type,
        detail=detail or {},
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def log_auth(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录认证相关操作"""
    return log_action(db, user_id, action, ActionType.AUTH, detail)


def log_project(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录项目管理操作"""
    return log_action(db, user_id, action, ActionType.PROJECT, detail)


def log_user(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录用户管理操作"""
    return log_action(db, user_id, action, ActionType.USER, detail)


def log_data(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录数据项管理操作"""
    return log_action(db, user_id, action, ActionType.DATA, detail)


def log_subject(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录受试者管理操作"""
    return log_action(db, user_id, action, ActionType.SUBJECT, detail)


def log_tag(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录标签管理操作"""
    return log_action(db, user_id, action, ActionType.TAG, detail)


def log_file(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录文件操作"""
    return log_action(db, user_id, action, ActionType.FILE, detail)


def log_analysis(db: Session, user_id: Optional[int], action: str, detail: Optional[Dict[str, Any]] = None):
    """记录数据分析操作"""
    return log_action(db, user_id, action, ActionType.ANALYSIS, detail)
