from typing import Annotated
from pydantic import BaseModel, Field

Quantity = Annotated[int, Field(ge=1, le=1_000)]
UnitPrice = Annotated[int, Field(ge=1, le=10_000_000)]


class OrderItemRequest(BaseModel):
    sku: str = Field(min_length=3, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    qty: Quantity
    unit_price: UnitPrice


class CreateOrderRequest(BaseModel):
    currency: str = Field(pattern="^(HUF|USD|EUR)")
    items: list[OrderItemRequest] = Field(min_length=1, max_length=50)


class OrderItemResponse(BaseModel):
    sku: str
    qty: int
    unit_price: int
    line_total: int


class OrderResponse(BaseModel):
    id: str
    status: str
    currency: str
    total_amount: int
    items: list[OrderItemResponse]
    created_at: str


class OrderSummaryResponse(BaseModel):
    id: str
    status: str
    currency: str
    total_amount: int
    created_at: str


class OrderListResponse(BaseModel):
    items: list[OrderSummaryResponse]
    next_cursor: str | None
