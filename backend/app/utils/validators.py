"""
输入验证辅助函数
"""
from typing import Any, List, Optional
import re


def validate_email(email: str) -> bool:
    """
    验证邮箱格式
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> tuple[bool, str]:
    """
    验证用户名格式
    
    Returns:
        (是否有效, 错误消息)
    """
    if not username or not isinstance(username, str):
        return False, "用户名不能为空"
    
    if len(username) < 3:
        return False, "用户名至少需要 3 个字符"
    
    if len(username) > 50:
        return False, "用户名不能超过 50 个字符"
    
    # 只允许字母、数字、下划线、连字符
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "用户名只能包含字母、数字、下划线和连字符"
    
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """
    验证密码强度
    
    Returns:
        (是否有效, 错误消息)
    """
    if not password or not isinstance(password, str):
        return False, "密码不能为空"
    
    if len(password) < 8:
        return False, "密码至少需要 8 个字符"
    
    if len(password) > 100:
        return False, "密码不能超过 100 个字符"
    
    # 检查是否包含字母和数字
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    
    if not (has_letter and has_digit):
        return False, "密码必须包含字母和数字"
    
    return True, ""


def validate_id(value: Any, name: str = "ID") -> tuple[bool, str]:
    """
    验证 ID 是否为正整数
    
    Returns:
        (是否有效, 错误消息)
    """
    if not isinstance(value, int):
        return False, f"{name} 必须为整数"
    
    if value <= 0:
        return False, f"{name} 必须大于 0"
    
    return True, ""


def validate_ids(values: List[Any], name: str = "ID 列表") -> tuple[bool, str]:
    """
    验证 ID 列表
    
    Returns:
        (是否有效, 错误消息)
    """
    if not isinstance(values, list):
        return False, f"{name} 必须为列表"
    
    if not values:
        return False, f"{name} 不能为空"
    
    for value in values:
        valid, msg = validate_id(value, name)
        if not valid:
            return False, msg
    
    return True, ""


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除危险字符
    """
    if not filename:
        return "unnamed"
    
    # 移除路径分隔符和其他危险字符
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    
    sanitized = filename
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # 限制长度
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized


def validate_pagination(skip: int, limit: int, max_limit: int = 100) -> tuple[bool, str]:
    """
    验证分页参数
    
    Returns:
        (是否有效, 错误消息)
    """
    if skip < 0:
        return False, "skip 不能为负数"
    
    if limit <= 0:
        return False, "limit 必须大于 0"
    
    if limit > max_limit:
        return False, f"limit 不能超过 {max_limit}"
    
    return True, ""


def validate_date_range(start_date: str, end_date: str) -> tuple[bool, str]:
    """
    验证日期范围
    
    Returns:
        (是否有效, 错误消息)
    """
    from datetime import datetime
    
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        if start > end:
            return False, "开始日期不能晚于结束日期"
        
        return True, ""
    except ValueError:
        return False, "日期格式无效，应为 ISO 格式"
