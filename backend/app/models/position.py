import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import utcnow


class Position(Base):
    """Posição real detida pelo utilizador: quantidade + preço médio de custo
    por ação. Independente da watchlist (podes ter uma posição numa ação que
    já não segues, ou seguir uma sem a possuir). Uma posição por ação por
    utilizador — sem histórico de transações individuais (ver HANDOFF.md);
    editar quantidade/preço médio substitui o valor guardado."""
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("user_id", "stock_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    stock: Mapped["Stock"] = relationship()  # noqa: F821
