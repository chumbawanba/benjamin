"""Jobs agendados: refresh diário de dados de mercado + avaliação/resumo semanal."""
import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Stock, StrategyTemplate, User, WatchlistItem
from app.services import agent, email_service, market_data

logger = logging.getLogger(__name__)


async def daily_refresh_job() -> int:
    """Atualiza os dados de mercado (preços + fundamentais) de todas as ações em
    alguma watchlist, para a app raramente precisar de consultar o Yahoo Finance em
    tempo real enquanto o utilizador a usa. Não avalia estratégias nem envia email —
    isso continua a ser feito pelo `weekly_job`. Devolve o nº de ações processadas
    (para testes)."""
    processed = 0
    async with SessionLocal() as db:
        stock_ids = (await db.execute(select(WatchlistItem.stock_id).distinct())).scalars().all()
        for stock_id in stock_ids:
            stock = (await db.execute(select(Stock).where(Stock.id == stock_id))).scalar_one_or_none()
            if stock is None:
                continue
            try:
                await market_data.ensure_fresh(db, stock)
                processed += 1
            except Exception:
                logger.exception("Falha ao atualizar dados de %s", stock.ticker)
        await db.commit()
    return processed


async def weekly_job() -> list[dict]:
    """Corre as avaliações semanais. Devolve as linhas do resumo (para testes)."""
    rows: list[dict] = []
    async with SessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        for user in users:
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
                            "strategy_name": template.name,
                        })
                    except Exception:
                        logger.exception("Falha ao avaliar %s / %s", stock.ticker, template.name)
        await db.commit()
    email_service.send_summary(rows)
    return rows
