from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import auth as firebase_auth
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
    GoogleLoginRequest,
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

@router.post("/google")
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        # -----------------------------------------
        # 1. Verify Firebase ID token
        # -----------------------------------------
        decoded_token = firebase_auth.verify_id_token(
            request.id_token
        )

    except Exception as e:
        print("Firebase token verification failed:", e)

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Google authentication token",
        )

    # -----------------------------------------
    # 2. Extract Google/Firebase information
    # -----------------------------------------
    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    name = decoded_token.get("name")

    if not firebase_uid:
        raise HTTPException(
            status_code=401,
            detail="Firebase UID not found",
        )

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email not provided by Google",
        )

    # -----------------------------------------
    # 3. Find user by Firebase UID
    # -----------------------------------------
    result = await db.execute(
        select(User).where(
            User.firebase_uid == firebase_uid
        )
    )

    user = result.scalar_one_or_none()

    # -----------------------------------------
    # 4. Create PostgreSQL user if new
    # -----------------------------------------
    if user is None:

        user = User(
            firebase_uid=firebase_uid,
            email=email,
            name=name,
        )

        db.add(user)

        await db.commit()
        await db.refresh(user)

    # -----------------------------------------
    # 5. Generate BayMax access token
    # -----------------------------------------
    access_token = create_access_token(
        str(user.id)
    )

    # -----------------------------------------
    # 6. Return same format as normal login
    # -----------------------------------------
    return {
        "accessToken": access_token
    }