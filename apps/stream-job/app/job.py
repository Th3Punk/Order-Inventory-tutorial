from __future__ import annotations

import json
from datetime import datetime, timezone

from pyflink.common import Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.time import Time, Duration
from pyflink.common.watermark_strategy import WatermarkStrategy, TimestampAssigner
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    DeliveryGuarantee,
    KafkaOffsetsInitializer,
    KafkaRecordSerializationSchema,
    KafkaSink,
    KafkaSource,
)
from pyflink.datastream.functions import ProcessWindowFunction
from pyflink.datastream.window import TumblingEventTimeWindows


def _extract_sku_events(raw: str):
    try:
        event = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return []

    if event.get("event_type") != "OrderCreated":
        return []

    occurred_at = event.get("created_at")
    payload = event.get("payload") or {}
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []

    try:
        dt = datetime.fromisoformat((occurred_at or "").replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    event_ts_ms = int(dt.timestamp() * 1000)

    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sku = item.get("sku")
        qty = item.get("qty")
        if not sku or not isinstance(qty, int):
            continue
        # (sku, qty, event_ts_ms)
        out.append((sku, qty, event_ts_ms))
    return out


class EventTimestampAssigner(TimestampAssigner):
    def extract_timestamp(self, value, record_timestamp) -> int:
        # value: (sku, qty, event_ts_ms)
        return value[2]


class SumPerWindow(ProcessWindowFunction):
    def process(self, key, context, elements):
        total = 0
        for e in elements:
            total += e[1]  # qty
        window_start = datetime.fromtimestamp(context.window().start / 1000, tz=timezone.utc).isoformat()
        window_end = datetime.fromtimestamp(context.window().end / 1000, tz=timezone.utc).isoformat()
        return [
            json.dumps(
                {
                    "sku": key,
                    "window_start": window_start,
                    "window_end": window_end,
                    "total_qty": total,
                },
                ensure_ascii=True,
            )
        ]


def main() -> None:
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers("kafka:9092")
        .set_topics("orders.events")
        .set_group_id("stream-job-v1")
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    sink = (
        KafkaSink.builder()
        .set_bootstrap_servers("kafka:9092")
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder().set_topic("orders.sku-stats").set_value_serialization_schema(SimpleStringSchema()).build()
        )
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
        .build()
    )

    stream = env.from_source(source, WatermarkStrategy.no_watermarks(), "orders-events")

    sku_events = stream.flat_map(
        _extract_sku_events,
        output_type=Types.TUPLE([Types.STRING(), Types.INT(), Types.LONG()]),
    )

    with_watermarks = sku_events.assign_timestamps_and_watermarks(
        WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_seconds(5)).with_timestamp_assigner(EventTimestampAssigner())
    )

    aggregated = (
        with_watermarks.key_by(lambda e: e[0], key_type=Types.STRING())
        .window(TumblingEventTimeWindows.of(Time.minutes(1)))
        .process(SumPerWindow(), output_type=Types.STRING())
    )

    aggregated.print()
    aggregated.sink_to(sink)

    env.execute("stream-job")


if __name__ == "__main__":
    main()
