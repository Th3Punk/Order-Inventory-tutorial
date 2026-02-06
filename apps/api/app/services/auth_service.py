from datetime import datetime, timedelta, timezone
import secrets
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.security.jwt import create_access_token
from app.security.passwords import verify_password, hash_password
from app.core.config import settings
from app.schemas.auth import TokenResponse
from app.repositories import auth_repository


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def get_refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=settings.refresh_ttl_seconds)


async def register_user(db: AsyncSession, email: str, password: str, role: str = "user") -> dict:
    existing = await auth_repository.get_user_by_email(db, email=email)
    if existing:
        # TODO: később egyedi hibakód/409
        raise ValueError("Email already exists")

    password_hash = hash_password(password)
    user = await auth_repository.create_user(db, email=email, password_hash=password_hash, role=role)
    return {"id": str(user.id), "email": user.email, "role": user.role}


async def login_user(db: AsyncSession, email: str, password: str) -> TokenResponse:
    user = await auth_repository.get_user_by_email(db, email=email)
    if not user or not verify_password(password, user.password_hash):
        # TODO: később egységes hiba
        raise ValueError("Invalid credentials")

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = generate_refresh_token()

    await auth_repository.create_refresh_token(
        db,
        user_id=str(user.id),
        token_hash=hash_refresh_token(refresh_token),
        expires_at=get_refresh_expiry(),
    )

    return TokenResponse(
        access_token=access_token,
        access_expires_in=settings.access_ttl_seconds,
        refresh_token=refresh_token,
        refresh_expires_in=settings.refresh_ttl_seconds,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    token_hash = hash_refresh_token(refresh_token)
    rt = await auth_repository.get_refresh_token(db, token_hash=token_hash)

    if not rt or rt.revoked_at is not None or rt.expires_at < datetime.now(timezone.utc):
        raise ValueError("Invalid refresh token")

    await auth_repository.revoke_refresh_token(db, token_hash)

    user = await auth_repository.get_user_by_id(db, user_id=str(rt.user_id))
    if not user:
        raise ValueError("User not found")
    access_token = create_access_token(subject=str(user.id), role=user.role)
    new_refresh_token = generate_refresh_token()

    await auth_repository.create_refresh_token(
        db,
        user_id=str(user.id),
        token_hash=hash_refresh_token(new_refresh_token),
        expires_at=get_refresh_expiry(),
    )

    return TokenResponse(
        access_token=access_token,
        access_expires_in=settings.access_ttl_seconds,
        refresh_token=new_refresh_token,
        refresh_expires_in=settings.refresh_ttl_seconds,
    )


async def logout(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    await auth_repository.revoke_refresh_token(db, token_hash)
