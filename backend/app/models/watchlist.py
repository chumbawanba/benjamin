import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import utcnow


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "stock_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    target_buy_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    target_sell_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    notes: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    # Alertas (ver app/services/alerts.py) - opt-in explícito por ação para o
    # alerta de mudança de sinal (o de preço já é opt-in implícito: só dispara
    # se target_buy_price/target_sell_price estiver preenchido). Os dois
    # "*_alert_triggered" guardam se a condição de preço já estava cumprida na
    # última corrida do job, para o alerta ser edge-triggered (dispara só na
    # transição para "cumprida", não em todas as corridas enquanto o preço
    # se mantém cruzado) - resetados a False quando o preço volta para o lado
    # "normal" do alvo.
    alert_on_signal: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    buy_alert_triggered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    sell_alert_triggered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    stock: Mapped["Stock"] = relationship()  # noqa: F821
