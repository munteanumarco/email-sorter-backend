from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import PyJWTError

from app.core.database import SessionLocal
from app.core.config import settings
from app.models import User

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
    tokenUrl="https://oauth2.googleapis.com/token",
)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization:
        raise credentials_exception

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise credentials_exception

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise credentials_exception
            
        return user
    except (PyJWTError, ValueError):
        raise credentials_exception

async def get_current_user_optional(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
) -> Optional[User]:
    """Like get_current_user but returns None if no valid auth"""
    try:
        return await get_current_user(db, authorization)
    except HTTPException:
        return None