from sqlalchemy.ext.asyncio import AsyncSession
from app.db.outbox_events import OutboxEvent


async def add_outbox_event(db: AsyncSession, event: OutboxEvent) -> None:
    db.add(event)
