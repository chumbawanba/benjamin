import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (UniqueConstraint("stock_id", "date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    high: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    low: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    close: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    volume: Mapped[int | None] = mapped_column(BigInteger)


class FundamentalsSnapshot(Base):
    __tablename__ = "fundamentals_snapshots"
    __table_args__ = (UniqueConstraint("stock_id", "date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    # Métricas adicionais de "posição financeira" (ver app/services/analyst.py e
    # HANDOFF.md) - revenue_growth/net_margin/roe em percentagem (ex: 12.34 =
    # 12.34%), current_ratio é um rácio simples (ativo circulante / passivo
    # circulante, ex: 1.5). Todos opcionais - Finnhub nem sempre os devolve.
    revenue_growth: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    net_margin: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    current_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))


class IndicatorValue(Base):
    __tablename__ = "indicator_values"
    __table_args__ = (UniqueConstraint("stock_id", "indicator_name", "date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))


class FxRateSnapshot(Base):
    """Cache diário de taxas de câmbio (ver app/services/fx.py) - usado para
    converter posições do portfolio (em moedas diferentes, ex: USD e EUR) para
    a moeda preferida do utilizador (User.preferred_currency)."""
    __tablename__ = "fx_rate_snapshots"
    __table_args__ = (UniqueConstraint("base_currency", "quote_currency", "date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
