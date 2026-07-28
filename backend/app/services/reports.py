"""Resumo periódico por email (ver app/scheduler.py::report_job). Lógica
extraída para aqui (em vez de viver dentro do job) para poder ser testada com
uma sessão/hora injetadas, tal como app/services/alerts.py."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Stock, StrategyTemplate, User, WatchlistItem
from app.services import agent, email_service

logger = logging.getLogger(__name__)

# Só reenvia o resumo periódico a um utilizador se já tiverem passado pelo
# menos este intervalo desde o último envio - evita duplicar o email caso o
# job corra mais que uma vez na hora-alvo, e garante cadência semanal mesmo
# que o utilizador mude report_day_of_week/report_hour a meio da semana.
MIN_REPORT_INTERVAL = timedelta(days=6)


async def generate_and_send_reports(db: AsyncSession, now: datetime | None = None) -> list[dict]:
    """Para cada utilizador, só gera e envia o resumo periódico se `now`
    (hora UTC atual, ver CLAUDE.md) corresponder ao dia/hora que escolheu
    (User.report_day_of_week/report_hour - ver GET/PUT
    /notifications/preferences) e ainda não tiver recebido um nas últimas
    MIN_REPORT_INTERVAL. Respeita User.email_reports_enabled - se desligado,
    salta o utilizador sem gastar avaliações. Devolve as linhas de todos os
    utilizadores para quem o resumo foi gerado nesta corrida (para testes)."""
    if now is None:
        now = datetime.now(timezone.utc)

    all_rows: list[dict] = []
    users = (await db.execute(select(User))).scalars().all()
    for user in users:
        if not user.email_reports_enabled:
            continue
        if now.weekday() != user.report_day_of_week or now.hour != user.report_hour:
            continue
        if user.last_report_sent_at is not None and now - user.last_report_sent_at < MIN_REPORT_INTERVAL:
            continue

        templates = (
            await db.execute(select(StrategyTemplate).where(
                StrategyTemplate.user_id == user.id, StrategyTemplate.is_active.is_(True)
            ))
        ).scalars().all()
        items = (
            await db.execute(
                select(WatchlistItem, Stock).join(Stock, WatchlistItem.stock_id == Stock.id)
                .where(WatchlistItem.user_id == user.id)
            )
        ).all()
        user_rows: list[dict] = []
        for template in templates:
            for item, stock in items:
                try:
                    ev = await agent.evaluate(db, stock.id, template.id, user.id)
                    user_rows.append({
                        "ticker": stock.ticker,
                        "buy_score": float(ev.buy_score),
                        "sell_score": float(ev.sell_score),
                        "recommendation": ev.recommendation,
                        "price": float(ev.price_at_evaluation) if ev.price_at_evaluation else None,
                        "strategy_name": template.name,
                    })
                except Exception:
                    logger.exception("Falha ao avaliar %s / %s", stock.ticker, template.name)
        user.last_report_sent_at = now
        await db.commit()
        email_service.send_summary(user.email, user_rows, user.unsubscribe_token)
        all_rows += user_rows
    return all_rows
