from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.schemas.orders import CreateOrderRequest, OrderItemResponse, OrderListResponse, OrderResponse, OrderSummaryResponse
from app.schemas.order_status import UpdateOrderStatusRequest
from app.services import orders_service
from app.api.deps import get_current_user, require_role
from app.cache.redis_client import redis
from app.cache.order_cache import get_cached_order, set_cached_order, invalidate_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: CreateOrderRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> OrderResponse:
    try:
        order = await orders_service.create_order_with_outbox(
            db=db, user_id=user["sub"], idempotency_key=idempotency_key, currency=data.currency, items=data.items
        )

    except ValueError:
        raise HTTPException(status_code=409, detail="Idempotency conflict")

    items_response = [
        OrderItemResponse(
            sku=item.sku,
            qty=item.qty,
            unit_price=item.unit_price,
            line_total=item.qty * item.unit_price,
        )
        for item in data.items
    ]

    return OrderResponse(
        id=str(order.id),
        status=order.status,
        currency=order.currency,
        total_amount=order.total_amount,
        items=items_response,
        created_at=order.created_at.isoformat(),
    )


@router.get("", response_model=OrderListResponse)
async def list_orders(
    db: AsyncSession = Depends(get_db), user=Depends(get_current_user), limit: int = 20, cursor: str | None = None, status: str | None = None
) -> OrderListResponse:
    orders, next_cursor = await orders_service.list_orders_for_user(db=db, user_id=user["sub"], limit=limit, cursor=cursor, status=status)
    items = [
        OrderSummaryResponse(
            id=str(order.id),
            status=order.status,
            currency=order.currency,
            total_amount=order.total_amount,
            created_at=order.created_at.isoformat(),
        )
        for order in orders
    ]

    return OrderListResponse(items=items, next_cursor=next_cursor)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    cached = await get_cached_order(redis, order_id)
    if cached:
        return cached

    order = await orders_service.get_order_detail(db, user["sub"], order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = [
        OrderItemResponse(
            sku=i.sku,
            qty=i.qty,
            unit_price=i.unit_price,
            line_total=i.qty * i.unit_price,
        )
        for i in order.items
    ]
    response = OrderResponse(
        id=str(order.id),
        status=order.status,
        currency=order.currency,
        total_amount=order.total_amount,
        items=items,
        created_at=order.created_at.isoformat(),
    )

    await set_cached_order(redis, order_id, response.model_dump(), ttl_seconds=60)
    return response


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_status(
    order_id: str,
    data: UpdateOrderStatusRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        order = await orders_service.update_order_status(
            db=db,
            user_id=user["sub"],
            order_id=order_id,
            new_status=data.status,
        )
    except ValueError:
        raise HTTPException(status_code=409, detail="Invalid status transition")

    await invalidate_order(redis, order_id)

    return OrderResponse(
        id=str(order.id),
        status=order.status,
        currency=order.currency,
        total_amount=order.total_amount,
        items=[],
        created_at=order.created_at.isoformat(),
    )


@router.get("/admin/orders")
async def admin_orders(
    user_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_role("admin")),
):
    orders = await orders_service.admin_list_orders(db, user_id, status, limit)
    return {
        "items": [
            {
                "id": str(o.id),
                "status": o.status,
                "total_amount": o.total_amount,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
    }
