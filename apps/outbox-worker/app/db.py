from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
