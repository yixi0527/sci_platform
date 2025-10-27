from typing import List, Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.roles import serialize_roles


DEFAULT_ROLES = ["researcher"]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _dump_roles(roles: Optional[List[str]]) -> str:
    if roles is None or len(roles) == 0:
        return serialize_roles(DEFAULT_ROLES)
    return serialize_roles(roles)


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return (
        db.query(User)
        .order_by(User.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.userId == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    user = User(
        username=user_in.username,
        passwordHash=pwd_context.hash(user_in.password),
        roles=_dump_roles(user_in.roles),
        realName=user_in.realName,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    if user_in.username is not None:
        user.username = user_in.username
    if user_in.password is not None:
        user.passwordHash = pwd_context.hash(user_in.password)
    if user_in.roles is not None:
        user.roles = _dump_roles(user_in.roles)
    if user_in.realName is not None:
        user.realName = user_in.realName
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
