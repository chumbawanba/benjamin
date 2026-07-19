import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import utcnow


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    strategy_template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategy_templates.id", ondelete="CASCADE"), nullable=False
    )
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    buy_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    sell_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    recommendation: Mapped[str] = mapped_column(String(10), nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text)
    price_at_evaluation: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    details: Mapped[list["EvaluationDetail"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationDetail(Base):
    __tablename__ = "evaluation_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )
    strategy_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategy_items.id", ondelete="CASCADE"), nullable=False
    )
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    contribution: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))

    evaluation: Mapped["Evaluation"] = relationship(back_populates="details")
