import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow

VALID_CATEGORIES = {"imovel", "outro"}


class OtherAsset(Base):
    """Ativo do utilizador fora do Portfolio de ações/ETFs/cash (imóvel,
    certificado de aforro/tesouro, etc. - ver ESTADO.md secção 11/pedido do
    Edgar). Espelho do Loan do lado do ativo: guarda só o valor atual, sem
    histórico de avaliações - editar substitui o valor guardado.
    `expected_return_pct` é opcional e usado na Projeção de património (cada
    ativo cresce à sua própria taxa em vez da taxa geral do portfolio de
    ações) - 0/None significa que o valor fica constante na projeção."""
    __tablename__ = "other_assets"
    __table_args__ = (CheckConstraint("category IN ('imovel', 'outro')", name="ck_other_assets_category"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expected_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
