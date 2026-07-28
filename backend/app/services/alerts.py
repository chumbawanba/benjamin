"""Deteção de alertas (preço-alvo atingido / mudança de sinal), corrida pelo
job diário (ver scheduler.py::alerts_job). Edge-triggered: só dispara na
transição de "não cumprida" para "cumprida" - não repete o mesmo alerta em
todas as corridas enquanto a condição se mantém (ver
WatchlistItem.buy_alert_triggered/sell_alert_triggered e a comparação com a
avaliação anterior para os sinais).

Alertas de preço são sempre verificados (o próprio target_buy_price/
target_sell_price já é o opt-in). Alertas de sinal só correm para os itens
com alert_on_signal=True - e só para esses é que agent.evaluate() é chamado
neste job (os restantes continuam a ser avaliados só quando o utilizador o
faz manualmente ou pelo report_job), para não gastar indicadores/Finnhub
extra em quem não pediu este alerta."""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Evaluation, Notification, StrategyTemplate, User, WatchlistItem
from app.services import agent, market_data, notifications

logger = logging.getLogger(__name__)


async def _check_price_alert(db: AsyncSession, user: User, item: WatchlistItem) -> list[Notification]:
    created: list[Notification] = []
    stock = item.stock
    try:
        await market_data.ensure_fresh(db, stock)
        last_price, _ = await market_data.get_price_change(db, stock.id)
    except Exception:
        logger.exception("Falha ao atualizar preço de %s para alertas", stock.ticker)
        return created
    if last_price is None:
        return created

    if item.target_buy_price is not None:
        if last_price <= item.target_buy_price and not item.buy_alert_triggered:
            note = await notifications.create_notification(
                db, user, kind="price_buy", stock=stock,
                message=(
                    f"{stock.ticker} atingiu o teu preço-alvo de compra: "
                    f"{last_price} <= {item.target_buy_price}"
                ),
            )
            created.append(note)
            item.buy_alert_triggered = True
        elif last_price > item.target_buy_price:
            item.buy_alert_triggered = False

    if item.target_sell_price is not None:
        if last_price >= item.target_sell_price and not item.sell_alert_triggered:
            note = await notifications.create_notification(
                db, user, kind="price_sell", stock=stock,
                message=(
                    f"{stock.ticker} atingiu o teu preço-alvo de venda: "
                    f"{last_price} >= {item.target_sell_price}"
                ),
            )
            created.append(note)
            item.sell_alert_triggered = True
        elif last_price < item.target_sell_price:
            item.sell_alert_triggered = False

    return created


async def _check_signal_alert(
    db: AsyncSession, user: User, item: WatchlistItem, templates: list[StrategyTemplate]
) -> list[Notification]:
    created: list[Notification] = []
    stock = item.stock
    for template in templates:
        previous = (
            await db.execute(
                select(Evaluation).where(
                    Evaluation.user_id == user.id, Evaluation.stock_id == stock.id,
                    Evaluation.strategy_template_id == template.id,
                ).order_by(Evaluation.run_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        try:
            new_eval = await agent.evaluate(db, stock.id, template.id, user.id)
        except Exception:
            logger.exception("Falha ao avaliar %s / %s para alertas", stock.ticker, template.name)
            continue
        if (
            previous is not None
            and new_eval.recommendation in ("BUY", "SELL")
            and new_eval.recommendation != previous.recommendation
        ):
            kind = "signal_buy" if new_eval.recommendation == "BUY" else "signal_sell"
            note = await notifications.create_notification(
                db, user, kind=kind, stock=stock,
                message=f'{stock.ticker}: o sinal de "{template.name}" mudou para {new_eval.recommendation}',
            )
            created.append(note)
    return created


async def check_alerts(db: AsyncSession, user_id: uuid.UUID | None = None) -> list[Notification]:
    """Corre a deteção de alertas para todos os utilizadores (ou só um, em
    testes). Devolve as notificações criadas nesta corrida."""
    created: list[Notification] = []
    query = select(User)
    if user_id is not None:
        query = query.where(User.id == user_id)
    users = (await db.execute(query)).scalars().all()

    for user in users:
        items = (
            await db.execute(
                select(WatchlistItem).options(selectinload(WatchlistItem.stock))
                .where(WatchlistItem.user_id == user.id)
            )
        ).scalars().all()
        if not items:
            continue

        templates = (
            await db.execute(select(StrategyTemplate).where(
                StrategyTemplate.user_id == user.id, StrategyTemplate.is_active.is_(True)
            ))
        ).scalars().all()

        for item in items:
            created += await _check_price_alert(db, user, item)
            if item.alert_on_signal and templates:
                created += await _check_signal_alert(db, user, item, templates)

        await db.flush()

    await db.commit()
    return created
