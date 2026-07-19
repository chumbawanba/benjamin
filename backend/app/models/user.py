import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Resumo do analista (Overview) - singleton por utilizador, atualizado
    # manualmente via POST /analyst/summary/refresh (nunca automático).
    analyst_summary: Mapped[str | None] = mapped_column(Text)
    analyst_summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Prompt de sistema personalizado (opcional) para o resumo do analista.
    # None = usa DEFAULT_SYSTEM_PROMPT (analyst.py). Editável via GET/PUT /analyst/prompt.
    analyst_prompt: Mapped[str | None] = mapped_column(Text)
