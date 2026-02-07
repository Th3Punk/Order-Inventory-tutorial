from datetime import datetime

from sqlalchemy import select, update, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.orders import Order
from app.db.order_items import OrderItem


async def add_order(db: AsyncSession, order: Order) -> None:
    db.add(order)


async def add_order_items(db: AsyncSession, items: list[OrderItem]) -> None:
    db.add_all(items)


async def get_order_by_id(db: AsyncSession, order_id: str) -> Order | None:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def update_order_status(db: AsyncSession, order_id: str, new_status: str) -> None:
    await db.execute(update(Order).where(Order.id == order_id).values(status=new_status))


async def get_order_by_idempotency(db: AsyncSession, user_id: str, idempotency_key: str) -> Order | None:
    result = await db.execute(select(Order).where(Order.user_id == user_id, Order.idempotency_key == idempotency_key))
    return result.scalar_one_or_none()


async def list_orders(
    db: AsyncSession, user_id: str, limit: int, cursor: tuple[datetime, str] | None = None, status: str | None = None
) -> list[Order]:
    query = select(Order).where(Order.user_id == user_id)
    if status:
        query = query.where(Order.status == status)
    if cursor:
        created_at, order_id = cursor
        query = query.where(and_(Order.created_at < created_at, Order.id < order_id))
    query = query.order_by(desc(Order.created_at), desc(Order.id)).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_order_with_items(db: AsyncSession, order_id: str) -> Order | None:
    query = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def admin_list_orders(
    db: AsyncSession,
    user_id: str | None,
    status: str | None,
    limit: int,
) -> list[Order]:
    query = select(Order)
    if user_id:
        query = query.where(Order.user_id == user_id)
    if status:
        query = query.where(Order.status == status)
    query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
