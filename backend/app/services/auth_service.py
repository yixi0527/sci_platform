from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from ..models import User
from ..schemas import auth as auth_schemas
from ..schemas import user as user_schemas
from ..services.user_service import pwd_context
import jwt
import os
from ..utils.roles import deserialize_roles

# Secret and algorithm - in production put secret in env
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
if not JWT_SECRET or JWT_SECRET == "change-me":
    raise RuntimeError(
        "JWT_SECRET is not set or is using the insecure default. Set the JWT_SECRET environment variable to a strong random value."
    )
JWT_ALG = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24


def authenticate_user(db: Session, username: str, password: str):
    """验证用户名和密码"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not pwd_context.verify(password, user.passwordHash):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)
    return encoded_jwt


def login(db: Session, params: auth_schemas.LoginParams):
    user = authenticate_user(db, params.username, params.password)
    if not user:
        return None
    token = create_access_token({"sub": user.username, "userId": user.userId})
    return token


def get_userInfo(db: Session, username: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    roles = deserialize_roles(user.roles)
    return {"roles": roles, "realName": user.realName}


def verify_access_token(db: Session, authorization: str | None):
    """Verify Authorization header (Bearer token), return user info dict or None."""
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    parts = authorization.split()
    if len(parts) != 2:
        return None
    token = parts[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        return None

    # payload contains sub=username and userId
    username = payload.get("sub")
    userId = payload.get("userId")
    user = None
    if username:
        user = db.query(User).filter(User.username == username).first()
    elif userId:
        user = db.query(User).filter(User.userId == userId).first()
    if not user:
        return None

    roles = deserialize_roles(user.roles)
    return {
        "roles": roles,
        "realName": user.realName,
        "username": user.username,
        "userId": user.userId,
    }
