from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import create_engine, text

from app.core.config import settings

router = APIRouter()


@router.get("/healthz")
def health() -> dict[str, str]:
    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
