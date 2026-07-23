import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    exchange: Mapped[str | None] = mapped_column(String(50))
    sector: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(10))
    # "stock" | "etf" - determina se refresh_fundamentals tenta obter
    # fundamentais de empresa (P/E, ROE, etc. não existem para um ETF da
    # mesma forma, ver market_data.py). Default "stock" porque é a esmagadora
    # maioria dos tickers existentes antes desta coluna existir.
    asset_type: Mapped[str] = mapped_column(String(10), nullable=False, default="stock", server_default="stock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
