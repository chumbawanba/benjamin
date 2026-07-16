"""Job semanal: avalia todas as watchlists com as checklists ativas e envia resumo."""
import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import ChecklistTemplate, Stock, User, WatchlistItem
from app.services import agent, email_service

logger = logging.getLogger(__name__)


async def weekly_job() -> list[dict]:
    """Corre as avaliações semanais. Devolve as linhas do resumo (para testes)."""
    rows: list[dict] = []
    async with SessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        for user in users:
            templates = (
                await db.execute(select(ChecklistTemplate).where(
                    ChecklistTemplate.user_id == user.id, ChecklistTemplate.is_active.is_(True)
                ))
            ).scalars().all()
            items = (
                await db.execute(
                    select(WatchlistItem, Stock).join(Stock, WatchlistItem.stock_id == Stock.id)
                    .where(WatchlistItem.user_id == user.id)
                )
            ).all()
            for template in templates:
                for item, stock in items:
                    try:
                        ev = await agent.evaluate(db, stock.id, template.id, user.id)
                        rows.append({
                            "ticker": stock.ticker,
                            "buy_score": float(ev.buy_score),
                            "sell_score": float(ev.sell_score),
                            "recommendation": ev.recommendation,
                            "price": float(ev.price_at_evaluation) if ev.price_at_evaluation else None,
                            "checklist_name": template.name,
                        })
                    except Exception:
                        logger.exception("Falha ao avaliar %s / %s", stock.ticker, template.name)
        await db.commit()
    email_service.send_summary(rows)
    return rows
