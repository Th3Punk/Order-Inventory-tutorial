from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_local


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with session_local() as session:
        yield session
