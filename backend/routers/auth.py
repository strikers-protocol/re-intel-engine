"""
Auth Router — /api/auth/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.utils.database import get_db
from backend.utils.auth import hash_password, verify_password, create_token, get_current_user
from backend.models.db_models import User
from backend.models.schemas import UserRegister, UserLogin, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check duplicate
    existing = await db.execute(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already taken")

    user = User(
        username  = data.username,
        email     = data.email,
        hashed_pw = hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_token(user.id, user.username)
    return TokenResponse(access_token=token, username=user.username, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user   = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    token = create_token(user.id, user.username)
    return TokenResponse(access_token=token, username=user.username, user_id=user.id)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
