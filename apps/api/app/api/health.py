from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine

router = APIRouter()


@router.get("/healthz")
async def health() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
