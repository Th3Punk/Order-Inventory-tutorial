from fastapi import APIRouter, HTTPException, Response, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services import auth_service
from app.db.deps import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register_user(db, data.email, data.password)
        return user
    except ValueError:
        raise HTTPException(status_code=409, detail="Email already exists")


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        tokens = await auth_service.login_user(db, data.email, data.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response.set_cookie(key="refresh_token", value=tokens.refresh_token, httponly=True, samesite="lax")
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        tokens = await auth_service.refresh_tokens(db, refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    response.set_cookie(key="refresh_token", value=tokens.refresh_token, httponly=True, samesite="lax")
    return tokens


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await auth_service.logout(db, refresh_token)

    response.delete_cookie(key="refresh_token")
    return None
