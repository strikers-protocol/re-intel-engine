"""
JWT Authentication utilities
Using hashlib instead of bcrypt to avoid version compatibility issues
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.utils.database import get_db
from backend.models.db_models import User
import hashlib, secrets, os

SECRET_KEY         = os.getenv("SECRET_KEY", "strikers_protocol_secret")
ALGORITHM          = "HS256"
TOKEN_EXPIRE_HOURS = 72
bearer             = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """SHA-256 + salt — no bcrypt dependency."""
    salt = secrets.token_hex(32)
    h    = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, h = hashed.split(":", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == h
    except Exception:
        return False


def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user   = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
