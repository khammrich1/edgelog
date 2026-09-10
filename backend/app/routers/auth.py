from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.requests import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import RefreshSession, User
from app.schemas import AccessTokenResponse, UserCreate, UserLogin, UserRead
from app.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE_NAME = "edgelog_refresh"


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip; treat naive values as UTC so comparisons are safe on any backend."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/auth")


async def _issue_refresh_session(db: AsyncSession, user_id) -> str:
    token = generate_refresh_token()
    session = RefreshSession(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=refresh_token_expiry(),
    )
    db.add(session)
    await db.commit()
    return token


@router.post("/register", response_model=AccessTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    refresh_token = await _issue_refresh_session(db, user.id)
    _set_refresh_cookie(response, refresh_token)

    return AccessTokenResponse(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/login", response_model=AccessTokenResponse)
async def login(payload: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        raise invalid_credentials

    refresh_token = await _issue_refresh_session(db, user.id)
    _set_refresh_cookie(response, refresh_token)

    return AccessTokenResponse(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if raw_token is None:
        raise unauthorized

    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
    session = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or _as_aware_utc(session.expires_at) < now:
        _clear_refresh_cookie(response)
        raise unauthorized

    # Rotate: revoke the used token and issue a fresh one.
    session.revoked_at = now
    await db.commit()

    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        _clear_refresh_cookie(response)
        raise unauthorized

    new_refresh_token = await _issue_refresh_session(db, user.id)
    _set_refresh_cookie(response, new_refresh_token)

    return AccessTokenResponse(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if raw_token is not None:
        token_hash = hash_refresh_token(raw_token)
        result = await db.execute(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
        session = result.scalar_one_or_none()
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return UserRead.model_validate(current_user)
