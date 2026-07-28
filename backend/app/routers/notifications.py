import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Notification, User
from app.schemas.common import NotificationOut, NotificationPreferencesIn, NotificationPreferencesOut
from app.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=30, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Centro de notificações in-app (alertas de preço/sinal + resumo
    periódico), mais recentes primeiro."""
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    return (await db.execute(query)).scalars().all()


@router.put("/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notification = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    notification.read_at = datetime.now(timezone.utc)
    await db.commit()


@router.get("/preferences", response_model=NotificationPreferencesOut)
async def get_preferences(user: User = Depends(get_current_user)):
    return NotificationPreferencesOut(
        email_reports_enabled=user.email_reports_enabled,
        email_alerts_enabled=user.email_alerts_enabled,
        report_day_of_week=user.report_day_of_week,
        report_hour=user.report_hour,
    )


@router.put("/preferences", response_model=NotificationPreferencesOut)
async def update_preferences(
    body: NotificationPreferencesIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.email_reports_enabled = body.email_reports_enabled
    user.email_alerts_enabled = body.email_alerts_enabled
    user.report_day_of_week = body.report_day_of_week
    user.report_hour = body.report_hour
    await db.commit()
    return NotificationPreferencesOut(
        email_reports_enabled=user.email_reports_enabled,
        email_alerts_enabled=user.email_alerts_enabled,
        report_day_of_week=user.report_day_of_week,
        report_hour=user.report_hour,
    )


@router.get("/unsubscribe/{token}", status_code=204)
async def unsubscribe(token: str, db: AsyncSession = Depends(get_db)):
    """Cancela subscrição de emails (resumo periódico + alertas) sem precisar
    de login - link presente no rodapé de todo email enviado (ver
    email_service.py). Sem auth de propósito: o token já funciona como prova
    de identidade suficiente para esta ação de baixo risco (só desliga
    emails, não expõe nem altera mais nada). Idempotente - chamar duas vezes
    não faz mal."""
    user = (
        await db.execute(select(User).where(User.unsubscribe_token == token))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Link inválido")
    user.email_reports_enabled = False
    user.email_alerts_enabled = False
    await db.commit()
