import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow


class Notification(Base):
    """Notificação in-app (centro de notificações) e, ao mesmo tempo, registo
    do que já foi disparado - usado por app/services/alerts.py para não repetir
    o mesmo alerta em todas as corridas do job diário (edge-triggered: só
    dispara quando a condição passa de "não cumprida" a "cumprida", ver
    WatchlistItem.buy_alert_triggered/sell_alert_triggered e a comparação com
    a avaliação anterior para sinais).

    kind: 'price_buy' | 'price_sell' | 'signal_buy' | 'signal_sell' | 'weekly_report'
    stock_id: None para 'weekly_report' (não é sobre uma ação específica)."""
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
