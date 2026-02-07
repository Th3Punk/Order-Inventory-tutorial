import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, text, ForeignKey, BigInteger, CheckConstraint, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    items = relationship("OrderItem", back_populates="order")

    __table_args__ = (
        CheckConstraint("status IN ('created', 'paid', 'canceled')", name="ck_order_status_valid"),
        CheckConstraint("currency IN ('USD', 'EUR', 'HUF')", name="ck_order_currency_valid"),
        UniqueConstraint("idempotency_key", "user_id", name="uq_order_idempotency_key_user_id"),
    )
