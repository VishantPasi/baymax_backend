from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)

from app.db.database import get_db
from app.db.models import User

from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    AuthResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/signup",
    response_model=AuthResponse,
)
async def signup(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(User).where(
            User.email == data.email
        )
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        auth_provider="email",
        name=data.name,
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        str(user.id)
    )

    return AuthResponse(
        access_token=access_token,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(User).where(
            User.email == data.email
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses Google login",
        )

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        str(user.id)
    )

    return AuthResponse(
        access_token=access_token,
    )

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "auth_provider": current_user.auth_provider,
    }