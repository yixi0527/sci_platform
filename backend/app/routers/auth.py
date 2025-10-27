from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.schemas import auth as auth_schemas
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=auth_schemas.LoginResult)
def login(params: auth_schemas.LoginParams, db: Session = Depends(get_db)):
    token = auth_service.login(db, params)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"accessToken": token}


@router.get("/codes", response_model=List[str])
def access_codes(
    username: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    if username is None:
        username = current_user.get("username")
    return []  # 不需要权限码


@router.post("/refresh", response_model=auth_schemas.LoginResult)
def refresh_token(current_user: dict = Depends(require_access_token)):
    new_token = auth_service.create_access_token(
        {"sub": current_user.get("username"), "userId": current_user.get("userId")}
    )
    return {"accessToken": new_token}


@router.post("/logout")
def logout():
    return {"ok": True}


@router.get("/me", response_model=auth_schemas.UserInfo)
def profile(current_user: dict = Depends(require_access_token)):
    return current_user
