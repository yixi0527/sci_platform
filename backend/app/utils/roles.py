import json
from typing import Iterable, List, Optional, Union


def deserialize_roles(raw: Union[str, Iterable[str], None]) -> List[str]:
    """Convert raw stored roles into a sanitized list of strings."""
    if raw in (None, ""):
        return []
    if isinstance(raw, list):
        return [str(role) for role in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return [raw]
        if isinstance(parsed, list):
            return [str(role) for role in parsed]
        if isinstance(parsed, str):
            return [parsed]
        return [str(parsed)]
    return [str(raw)]


def serialize_roles(roles: Optional[Union[str, Iterable[str]]]) -> str:
    """Serialize roles into JSON string for database persistence."""
    if roles is None:
        return json.dumps(["researcher"])
    if isinstance(roles, str):
        try:
            parsed = json.loads(roles)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return json.dumps([str(role) for role in parsed])
        return json.dumps([roles])
    try:
        return json.dumps([str(role) for role in roles])
    except TypeError:
        return json.dumps([str(roles)])


def get_user_roles(user_dict: dict) -> List[str]:
    """从用户字典中获取角色列表
    
    Args:
        user_dict: 包含 'roles' 字段的用户字典
        
    Returns:
        角色列表
    """
    roles = user_dict.get('roles', [])
    return deserialize_roles(roles)


def is_admin_or_tutor(user_dict: dict) -> bool:
    """检查用户是否是管理员或导师
    
    Args:
        user_dict: 包含 'roles' 字段的用户字典
        
    Returns:
        如果用户是 admin 或 tutor 返回 True，否则返回 False
    """
    roles = get_user_roles(user_dict)
    return 'admin' in roles or 'tutor' in roles
