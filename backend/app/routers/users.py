from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.schemas.auth import UserInfo
from app.services import user_service

router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[Depends(require_access_token)],
)

@router.get("/info", response_model=UserInfo)
def userInfo(_request: Request, userinfo: dict = Depends(require_access_token)):
    return userinfo

@router.get("/", response_model=List[UserRead])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    users = user_service.list_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    return user


@router.post("/", response_model=UserRead, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        user = user_service.create_user(db, user_in)
    except IntegrityError as e:
        db.rollback()
        raw = ""
        try:
            # psycopg/mysql driver details may live in e.orig or in args
            if hasattr(e, "orig") and e.orig is not None:
                raw = str(e.orig)
            else:
                raw = str(e)
        except Exception:
            raw = str(e)

        lower = raw.lower()
        if "username" in lower or "`username`" in lower or "unique_username" in lower:
            detail = "用户名已存在"
        elif "realname" in lower:
            detail = "真实姓名已存在\n为避免管理混乱，重名情况请作区分"
        elif "duplicate" in lower or "unique" in lower:
            detail = f"唯一性冲突: {raw}"
        else:
            detail = f"数据库错误: {raw}"

        raise HTTPException(status_code=400, detail=detail)
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    user = user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    try:
        user = user_service.update_user(db, user, user_in)
    except IntegrityError as e:
        try:
            db.rollback()
        except Exception:
            pass

        raw = ""
        try:
            if hasattr(e, "orig") and e.orig is not None:
                raw = str(e.orig)
            else:
                raw = str(e)
        except Exception:
            raw = str(e)

        lower = raw.lower()
        if "username" in lower or "`username`" in lower:
            detail = "用户名已存在"
        elif "realname" in lower or "real_name" in lower or "real name" in lower:
            detail = "真实姓名已存在"
        elif "duplicate" in lower or "unique" in lower:
            detail = f"唯一性冲突: {raw}"
        else:
            detail = f"数据库错误: {raw}"

        raise HTTPException(status_code=400, detail=detail)
    return user


@router.delete("/{user_id}", status_code=200)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    user_service.delete_user(db, user)
    return None
