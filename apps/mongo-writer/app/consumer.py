from __future__ import annotations

import json
import logging
import signal
import sys
from datetime import datetime, timezone

from confluent_kafka import Consumer, KafkaException
from pymongo import MongoClient, UpdateOne

from app.config import settings

logger = logging.getLogger("mongo-writer")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _parse_stats_message(raw: str) -> dict | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("invalid json payload, skipping")
        return None

    sku = data.get("sku")
    window_start = data.get("window_start")
    window_end = data.get("window_end")
    total_qty = data.get("total_qty")
    if not sku or not window_start or not window_end or total_qty is None:
        logger.warning("missing required fields, skipping: %s", data)
        return None

    return {
        "sku": sku,
        "window_start": window_start,
        "window_end": window_end,
        "total_qty": total_qty,
    }


def _parse_audit_message(raw: str) -> dict | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("invalid audit json payload, skipping")
        return None

    event_type = data.get("event_type")
    occurred_at = data.get("created_at") or data.get("occurred_at")
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else None
    if payload is None and isinstance(data.get("data"), str):
        try:
            payload = json.loads(data["data"])
        except json.JSONDecodeError:
            payload = None

    order_id = data.get("order_id")
    if not order_id and payload:
        order_id = payload.get("order_id")
    if not order_id:
        order_id = data.get("aggregate_id")

    if not occurred_at:
        occurred_at = datetime.now(timezone.utc).isoformat()

    if not event_type or not order_id:
        logger.warning("missing audit fields, skipping: %s", data)
        return None

    return {
        "order_id": order_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "data": payload or data,
    }


def _ensure_indexes(stats_collection, audit_collection) -> None:
    stats_collection.create_index([("sku", 1), ("window_start", 1)], unique=True)
    audit_collection.create_index([("order_id", 1), ("occurred_at", 1)])


def main() -> None:
    _setup_logging()

    mongo = MongoClient(settings.mongo_url)
    stats_collection = mongo[settings.mongo_db][settings.mongo_collection]
    audit_collection = mongo[settings.mongo_db][settings.mongo_audit_collection]
    _ensure_indexes(stats_collection, audit_collection)

    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([settings.kafka_topic, settings.kafka_audit_topic])

    running = True

    def _stop(*_args) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    logger.info(
        "mongo-writer started (topics=%s,%s)",
        settings.kafka_topic,
        settings.kafka_audit_topic,
    )

    try:
        while running:
            msg = consumer.poll(settings.poll_timeout_seconds)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())

            raw_value = msg.value().decode("utf-8")
            topic = msg.topic()

            if topic == settings.kafka_topic:
                payload = _parse_stats_message(raw_value)
                if payload is None:
                    continue
                now = datetime.now(timezone.utc).isoformat()
                key = {"sku": payload["sku"], "window_start": payload["window_start"]}
                update = {
                    "$set": {
                        "window_end": payload["window_end"],
                        "total_qty": payload["total_qty"],
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                }
                stats_collection.bulk_write([UpdateOne(key, update, upsert=True)])
            elif topic == settings.kafka_audit_topic:
                payload = _parse_audit_message(raw_value)
                if payload is None:
                    continue
                audit_collection.insert_one(payload)
            else:
                logger.warning("unexpected topic %s, skipping", topic)
    except Exception:
        logger.exception("mongo-writer crashed")
        sys.exit(1)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
