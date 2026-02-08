from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from confluent_kafka import Producer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import session_local
from app.outbox_repository import fetch_outbox_batch, mark_published, mark_retry, mark_failed

logger = logging.getLogger(__name__)


def _make_producer() -> Producer:
    return Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})


def _publish_event(producer: Producer, topic: str, key: str, value: dict[str, Any]) -> None:
    delivery_error: Exception | None = None

    def _delivery(err, msg):
        nonlocal delivery_error
        if err is not None:
            delivery_error = err

    producer.produce(topic=topic, key=key.encode("utf-8"), value=json.dumps(value).encode("utf-8"), on_delivery=_delivery)

    remaining = producer.flush(settings.outbox_publish_timeout_seconds)
    if remaining > 0:
        raise RuntimeError(f"Kafka publish timed out, {remaining} message(s) not delivered")

    if delivery_error is not None:
        raise RuntimeError(f"Kafka publish failed: {delivery_error}")


async def _process_batch(db: AsyncSession, producer: Producer) -> int:
    rows = await fetch_outbox_batch(db, settings.poll_batch_size)
    if not rows:
        return 0

    processed = 0

    for row in rows:
        try:
            payload = {"event_type": row.event_type, "aggregate_id": row.aggregate_id, "payload": row.payload, "created_at": row.created_at}
            _publish_event(producer=producer, topic=settings.outbox_topic, key=row.aggregate_id, value=payload)

            await mark_published(db, [row.id])
            await db.commit()
            processed += 1

        except Exception as ex:
            await mark_retry(db, [row.id], str(ex))
            await db.commit()

            if row.publish_attempts + 1 >= settings.outbox_max_retries:
                _publish_event(
                    producer=producer,
                    topic=settings.outbox_dlq_topic,
                    key=row.aggregate_id,
                    value={
                        "event_type": row.event_type,
                        "aggregate_id": row.aggregate_id,
                        "payload": row.payload,
                        "created_at": row.created_at,
                        "error": str(ex),
                    },
                )
                await mark_failed(db, [row.id])
                await db.commit()

    return processed


async def run_worker() -> None:
    producer = _make_producer()

    while True:
        async with session_local() as db:
            try:
                processed = await _process_batch(db, producer)
            except Exception:
                logger.exception("Outbox worker failed; rolling back")
                await db.rollback()
                processed = 0

        if processed == 0:
            await asyncio.sleep(settings.outbox_poll_interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
