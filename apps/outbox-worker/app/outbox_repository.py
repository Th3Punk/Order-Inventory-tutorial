from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import ARRAY, UUID


@dataclass(frozen=True)
class OutboxRow:
    id: str
    event_type: str
    aggregate_id: str
    payload: dict[str, Any]
    created_at: str
    publish_attempts: int


async def fetch_outbox_batch(db: AsyncSession, batch_size: int) -> list[OutboxRow]:
    """
    Kivesz egy batch-nyi, még nem publikált outbox rekordot.
    FOR UPDATE SKIP LOCKED biztosítja, hogy párhuzamos worker ne vigye ugyanazt.
    """
    query = text(
        """
        SELECT id::text, event_type, aggregate_id::text, payload_json, created_at::text, publish_attempts
        FROM outbox_events
        WHERE published_at IS NULL AND failed_at IS NULL
        ORDER BY created_at ASC
        LIMIT :limit
        FOR UPDATE SKIP LOCKED
        """
    )
    result = await db.execute(query, {"limit": batch_size})
    rows = result.mappings().all()

    return [
        OutboxRow(
            id=row["id"],
            event_type=row["event_type"],
            aggregate_id=row["aggregate_id"],
            payload=row["payload_json"],
            created_at=row["created_at"],
            publish_attempts=row["publish_attempts"],
        )
        for row in rows
    ]


async def mark_published(db: AsyncSession, ids: list[str]) -> None:
    """
    Publikáltként jelöli a feldolgozott outbox rekordokat.
    """
    if not ids:
        return

    query = text(
        """
        UPDATE outbox_events
        SET published_at = NOW()
        WHERE id = ANY(:ids)
        """
    ).bindparams(bindparam("ids", type_=ARRAY(UUID)))
    await db.execute(query, {"ids": ids})


async def mark_retry(db: AsyncSession, ids: list[str], error_message: str) -> None:
    if not ids:
        return
    query = text(
        """
        UPDATE outbox_events
        SET publish_attempts = publish_attempts + 1,
            last_error = :error
        WHERE id = ANY(:ids)
        """
    ).bindparams(bindparam("ids", type_=ARRAY(UUID)))
    await db.execute(query, {"ids": ids, "error": error_message})


async def mark_failed(db: AsyncSession, ids: list[str]) -> None:
    if not ids:
        return
    query = text(
        """
        UPDATE outbox_events
        SET failed_at = NOW()
        WHERE id = ANY(:ids)
        """
    ).bindparams(bindparam("ids", type_=ARRAY(UUID)))
    await db.execute(query, {"ids": ids})
