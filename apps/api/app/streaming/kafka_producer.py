import json
from confluent_kafka import Producer

from app.core.config import settings

_producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})


def publish_event(topic: str, key: str, value: dict) -> None:
    _producer.produce(topic, key=key.encode("utf-8"), value=json.dumps(value).encode("utf-8"))
    _producer.flush()
