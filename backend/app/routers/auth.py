"""
认证路由
提供登录、登出、token刷新、用户信息查询等接口
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas import auth as auth_schemas
from app.services import auth_service
from app.utils.logger import api_logger as logger
from app.utils.log_helper import log_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=auth_schemas.LoginResult)
def login(params: auth_schemas.LoginParams, db: Session = Depends(get_db)):
    """
    用户登录
    
    Args:
        params: 登录参数（用户名和密码）
        
    Returns:
        LoginResult: 包含访问令牌的登录结果
        
    Raises:
        401: 用户名或密码错误
    """
    logger.info(f"Login attempt for user: {params.username}")
    token = auth_service.login(db, params)
    if not token:
        logger.warning(f"Failed login attempt for user: {params.username}")
        # 记录失败的登录尝试
        log_auth(db, None, 'login_failed', {'username': params.username})
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    logger.info(f"Successful login for user: {params.username}")
    
    # 获取用户ID用于记录日志
    user_info = auth_service.verify_access_token(db, f"Bearer {token}")
    if user_info:
        log_auth(db, user_info.get('userId'), 'login_success', {'username': params.username})
    
    return {"accessToken": token}


@router.get("/codes", response_model=List[str])
def access_codes(
    username: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    获取访问权限码（预留接口，当前返回空列表）
    
    Args:
        username: 用户名（可选，默认为当前用户）
        
    Returns:
        List[str]: 权限码列表
    """
    if username is None:
        username = current_user.get("username")
    logger.debug(f"Access codes requested for user: {username}")
    return []  # 当前系统不使用权限码


@router.post("/refresh", response_model=auth_schemas.LoginResult)
def refresh_token(current_user: dict = Depends(require_access_token)):
    """
    刷新访问令牌
    
    Args:
        current_user: 当前用户信息（从token中解析）
        
    Returns:
        LoginResult: 包含新访问令牌的结果
    """
    username = current_user.get("username")
    logger.info(f"Token refresh for user: {username}")
    
    new_token = auth_service.create_access_token(
        {"sub": username, "userId": current_user.get("userId")}
    )
    return {"accessToken": new_token}


@router.post("/logout")
def logout(current_user: dict = Depends(require_access_token), db: Session = Depends(get_db)):
    """
    用户登出（客户端需清除token）
    
    Returns:
        dict: 登出成功标识
    """
    username = current_user.get("username")
    logger.info(f"User logged out: {username}")
    
    # 记录登出日志
    log_auth(db, current_user.get('userId'), 'logout', {'username': username})
    
    return {"ok": True}


@router.get("/me", response_model=auth_schemas.UserInfo)
def profile(current_user: dict = Depends(require_access_token)):
    """
    获取当前用户信息
    
    Returns:
        UserInfo: 用户信息
    """
    logger.debug(f"Profile requested for user: {current_user.get('username')}")
    return current_user
