import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow


class PatrimonySnapshot(Base):
    """Registo manual do património do utilizador numa data (pedido do
    Edgar: "manter um histórico do meu património" - Position/OtherAsset/Loan
    só guardam o valor atual, sem histórico, por isso o utilizador tira
    "fotografias" pontuais para poder ver a evolução ao longo do tempo).

    Guarda o breakdown completo (stocks/cash/outros ativos/dívida) em vez de
    só o total, para se poder decompor o que mudou entre duas datas (ex.:
    compra de casa = cash desce, outros ativos sobe, dívida sobe). Uma
    entrada por utilizador+data - criar uma nova entrada para uma data já
    existente substitui a anterior (upsert), nunca há duas fotografias no
    mesmo dia."""
    __tablename__ = "patrimony_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_patrimony_snapshots_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    stocks_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    cash_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    other_assets_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    loans_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
