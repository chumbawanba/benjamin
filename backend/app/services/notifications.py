"""Centro de notificações in-app + disparo de email (opcional, por
preferência do utilizador). Usado por app/services/alerts.py (preço/sinal) e
scheduler.py::report_job (resumo periódico)."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, Stock, User
from app.services import email_service

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession, user: User, kind: str, message: str, stock: Stock | None = None,
) -> Notification:
    """Grava sempre a notificação in-app; envia também por email se o
    utilizador tiver o toggle correspondente ligado (email_reports_enabled
    para 'weekly_report', email_alerts_enabled para os restantes kinds)."""
    notification = Notification(
        user_id=user.id, stock_id=stock.id if stock else None, kind=kind, message=message,
    )
    db.add(notification)
    await db.flush()

    wants_email = user.email_reports_enabled if kind == "weekly_report" else user.email_alerts_enabled
    if wants_email:
        try:
            email_service.send_notification_email(user.email, message, user.unsubscribe_token)
        except Exception:
            logger.exception("Falha ao enviar email de notificação (%s) para %s", kind, user.email)

    return notification
