from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import auth_service


async def require_access_token(
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    user_info = auth_service.verify_access_token(db, authorization)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing token")
    return user_info
