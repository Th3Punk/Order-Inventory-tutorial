from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orders import Order
from app.db.order_items import OrderItem
from app.db.outbox_events import OutboxEvent
from app.schemas.orders import OrderItemRequest
from app.repositories import orders_repository, outbox_repository


def calculate_total(items: list[OrderItemRequest]) -> int:
    return sum(item.qty * item.unit_price for item in items)


def parse_cursor(cursor: str) -> tuple[datetime, str]:
    created_at_str, order_id = cursor.split("|", 1)
    return datetime.fromisoformat(created_at_str), order_id


def make_cursor(created_at: datetime, order_id: str) -> str:
    return f"{created_at.isoformat()}|{order_id}"


async def create_order_with_outbox(db: AsyncSession, user_id: str, idempotency_key: str, currency: str, items: list[OrderItemRequest]) -> Order:
    existing = await orders_repository.get_order_by_idempotency(db, user_id=user_id, idempotency_key=idempotency_key)
    if existing:
        raise ValueError("Idempotency conflict")

    total = calculate_total(items)

    order = Order(
        user_id=user_id,
        status="created",
        currency=currency,
        total_amount=total,
        idempotency_key=idempotency_key,
    )

    await orders_repository.add_order(db, order)
    await db.flush()

    order_items = [
        OrderItem(
            order_id=order.id,
            sku=item.sku,
            qty=item.qty,
            unit_price=item.unit_price,
        )
        for item in items
    ]

    outbox = OutboxEvent(
        aggregate_type="order",
        aggregate_id=order.id,
        event_type="OrderCreated",
        payload_json={"order_id": str(order.id)},
        created_at=datetime.now(timezone.utc),
    )

    await orders_repository.add_order_items(db, order_items)
    await outbox_repository.add_outbox_event(db, outbox)
    await db.commit()
    await db.refresh(order)

    return order


async def list_orders_for_user(
    db: AsyncSession,
    user_id: str,
    limit: int,
    cursor: str | None,
    status: str | None,
) -> tuple[list[Order], str | None]:
    parsed = parse_cursor(cursor) if cursor else None
    orders = await orders_repository.list_orders(db, user_id, limit, parsed, status)

    next_cursor = None
    if len(orders) == limit:
        last = orders[-1]
        next_cursor = make_cursor(last.created_at, str(last.id))

    return orders, next_cursor


async def get_order_detail(db: AsyncSession, user_id: str, order_id: str) -> Order | None:
    order = await orders_repository.get_order_with_items(db, order_id=order_id)
    if not order or str(order.user_id) != user_id:
        return None
    return order


async def update_order_status(
    db: AsyncSession,
    user_id: str,
    order_id: str,
    new_status: str,
) -> Order:
    order = await orders_repository.get_order_by_id(db, order_id)
    if not order or str(order.user_id) != user_id:
        raise ValueError("Not found")

    if order.status != "created" or new_status not in ("paid", "canceled"):
        raise ValueError("Invalid transition")

    await orders_repository.update_order_status(db, order_id, new_status)

    outbox = OutboxEvent(
        aggregate_type="order",
        aggregate_id=order.id,
        event_type="OrderPaid" if new_status == "paid" else "OrderCanceled",
        payload_json={"order_id": str(order.id)},
        created_at=datetime.now(timezone.utc),
    )
    await outbox_repository.add_outbox_event(db, outbox)

    await db.commit()
    await db.refresh(order)
    return order


async def admin_list_orders(
    db: AsyncSession,
    user_id: str | None,
    status: str | None,
    limit: int,
) -> list[Order]:
    return await orders_repository.admin_list_orders(db, user_id, status, limit)
