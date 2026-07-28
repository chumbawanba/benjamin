import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_unsubscribe_token() -> str:
    return secrets.token_urlsafe(32)


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
    # Moeda em que o portfolio é apresentado (conversão via app/services/fx.py) -
    # útil para quem tem posições em várias moedas (ex: ações US em USD e europeias
    # em EUR). Editável via GET/PUT /portfolio/currency.
    preferred_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR", server_default="EUR")
    # Data/hora em que aceitou a Política de Privacidade e de Cookies no registo
    # (obrigatório desde então - ver RegisterIn/auth.py). Nullable porque
    # utilizadores criados antes desta funcionalidade não têm este campo
    # preenchido retroativamente.
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Notificações/alertas (ver app/services/alerts.py, app/routers/notifications.py):
    # email_reports_enabled controla o resumo periódico (report_job);
    # email_alerts_enabled controla os emails de alerta de preço/sinal
    # disparados pelo job diário. As notificações in-app (tabela
    # Notification) são sempre criadas independentemente destes toggles -
    # só controlam se, além disso, sai um email. unsubscribe_token permite um
    # link de cancelar subscrição sem login (obrigatório em qualquer email
    # periódico/marketing-like) - gerado uma vez, nunca muda.
    email_reports_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    email_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    unsubscribe_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=new_unsubscribe_token
    )
    # Dia/hora (sempre UTC, ver CLAUDE.md) em que o utilizador escolhe receber o
    # resumo periódico - substitui o antigo cron fixo (sáb 08:00 UTC para
    # todos). report_day_of_week segue datetime.weekday() (0=segunda ...
    # 6=domingo); os valores por omissão preservam o comportamento anterior.
    # last_report_sent_at evita reenviar o mesmo resumo se o job (agora
    # horário, ver scheduler.py::report_job) correr mais que uma vez na
    # hora-alvo, e garante cadência semanal mesmo que o utilizador mude as
    # preferências a meio da semana.
    report_day_of_week: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)
    report_hour: Mapped[int] = mapped_column(Integer, default=8, server_default="8", nullable=False)
    last_report_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
