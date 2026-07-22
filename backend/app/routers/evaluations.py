import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Evaluation, StrategyItem, StrategyTemplate, User, WatchlistItem
from app.schemas.common import (
    BacktestChartOut, BacktestPointOut, BacktestTradeOut, EvaluationOut, RunEvaluationIn, StockOut,
    StrategySignalGroupOut, StrategySignalOut,
)
from app.security import get_current_user
from app.services import agent, backtest_core, market_data

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/run", response_model=list[EvaluationOut])
async def run_evaluation(
    body: RunEvaluationIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    template = (
        await db.execute(select(StrategyTemplate).where(
            StrategyTemplate.id == body.template_id, StrategyTemplate.user_id == user.id
        ))
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Estratégia não encontrada")

    if body.stock_id is not None:
        in_watchlist = (
            await db.execute(select(WatchlistItem).where(
                WatchlistItem.user_id == user.id, WatchlistItem.stock_id == body.stock_id
            ))
        ).scalar_one_or_none()
        if in_watchlist is None:
            raise HTTPException(status_code=404, detail="Ação não está na watchlist")
        stock_ids = [body.stock_id]
    else:
        stock_ids = (
            await db.execute(
                select(WatchlistItem.stock_id).where(WatchlistItem.user_id == user.id)
            )
        ).scalars().all()

    results = []
    for stock_id in stock_ids:
        evaluation = await agent.evaluate(db, stock_id, template.id, user.id)
        results.append(evaluation.id)
    await db.commit()

    rows = (
        await db.execute(
            select(Evaluation).options(selectinload(Evaluation.details))
            .where(Evaluation.id.in_(results))
        )
    ).scalars().all()
    return rows


@router.get("/latest", response_model=list[EvaluationOut])
async def latest_evaluations(
    template_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Avaliação mais recente de cada ação da watchlist. Sem template_id,
    devolve a mais recente entre TODAS as estratégias por ação (histórico,
    mantido por compatibilidade) - mas isso mistura estratégias diferentes
    sem indicação de qual é qual, por isso o Feed (frontend) passa sempre o
    template_id da estratégia selecionada no seletor."""
    stock_ids = (
        await db.execute(select(WatchlistItem.stock_id).where(WatchlistItem.user_id == user.id))
    ).scalars().all()
    out = []
    for stock_id in stock_ids:
        query = (
            select(Evaluation).options(selectinload(Evaluation.details))
            .where(Evaluation.user_id == user.id, Evaluation.stock_id == stock_id)
        )
        if template_id is not None:
            query = query.where(Evaluation.strategy_template_id == template_id)
        row = (
            await db.execute(query.order_by(Evaluation.run_at.desc()).limit(1))
        ).scalar_one_or_none()
        if row:
            out.append(row)
    out.sort(key=lambda e: float(e.buy_score), reverse=True)
    return out


@router.get("/latest-by-strategy", response_model=list[StrategySignalGroupOut])
async def latest_by_strategy(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Sinais BUY/SELL mais recentes, agrupados por estratégia ativa (HOLD é
    omitido). Usado no separador "Sinais" do Overview — em vez de uma lista
    plana da watchlist, cada estratégia mostra só as ações onde disparou um
    sinal de compra ou venda. Ordem dentro de cada grupo segue a ordem manual
    da watchlist (display_order)."""
    templates = (
        await db.execute(
            select(StrategyTemplate).where(
                StrategyTemplate.user_id == user.id, StrategyTemplate.is_active.is_(True)
            )
        )
    ).scalars().all()
    watchlist_items = (
        await db.execute(
            select(WatchlistItem).options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.display_order.asc(), WatchlistItem.added_at.desc())
        )
    ).scalars().all()

    groups = []
    for template in templates:
        signals = []
        for item in watchlist_items:
            evaluation = (
                await db.execute(
                    select(Evaluation).where(
                        Evaluation.user_id == user.id,
                        Evaluation.stock_id == item.stock_id,
                        Evaluation.strategy_template_id == template.id,
                    ).order_by(Evaluation.run_at.desc()).limit(1)
                )
            ).scalar_one_or_none()
            if evaluation is None or evaluation.recommendation == "HOLD":
                continue
            last_price, price_change_pct = await market_data.get_price_change(db, item.stock_id)
            signals.append(StrategySignalOut(
                stock=StockOut.model_validate(item.stock),
                recommendation=evaluation.recommendation,
                buy_score=evaluation.buy_score, sell_score=evaluation.sell_score,
                run_at=evaluation.run_at,
                last_price=last_price, price_change_pct=price_change_pct,
            ))
        groups.append(StrategySignalGroupOut(
            strategy_id=template.id, strategy_name=template.name,
            horizon=template.horizon, signals=signals,
        ))
    return groups


@router.get("/backtest-chart", response_model=BacktestChartOut)
async def backtest_chart(
    template_id: uuid.UUID, stock_id: uuid.UUID,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Simula, para UMA ação, o que os critérios ATUALMENTE guardados e ativos
    da estratégia teriam feito nos últimos ~365 dias — compra tudo ao 1º sinal
    BUY, vende tudo ao 1º sinal SELL seguinte (mesmo motor do otimizador, ver
    backtest_core.simulate). Usado para desenhar o gráfico de compras/vendas
    no separador Avaliações."""
    template = (
        await db.execute(select(StrategyTemplate).where(
            StrategyTemplate.id == template_id, StrategyTemplate.user_id == user.id
        ))
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Estratégia não encontrada")

    in_watchlist = (
        await db.execute(select(WatchlistItem).where(
            WatchlistItem.user_id == user.id, WatchlistItem.stock_id == stock_id
        ))
    ).scalar_one_or_none()
    if in_watchlist is None:
        raise HTTPException(status_code=404, detail="Ação não está na watchlist")

    items_rows = (
        await db.execute(
            select(StrategyItem).where(
                StrategyItem.template_id == template_id, StrategyItem.is_active.is_(True)
            ).order_by(StrategyItem.display_order.asc().nulls_last())
        )
    ).scalars().all()
    if not items_rows:
        raise HTTPException(status_code=400, detail="Esta estratégia não tem critérios ativos")
    items = [
        {
            "id": i.id, "metric": i.metric, "operator": i.operator,
            "threshold_value": i.threshold_value, "threshold_value_max": i.threshold_value_max,
            "weight": i.weight, "direction": i.direction,
        }
        for i in items_rows
    ]

    snapshots = await market_data.get_price_history(db, stock_id, days=365)
    if len(snapshots) < backtest_core.MIN_HISTORY_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Histórico de preços insuficiente para backtest (mínimo {backtest_core.MIN_HISTORY_DAYS} dias)",
        )

    closes = [float(s.close) for s in snapshots]
    dates = [s.date for s in snapshots]
    fundamentals_row = await market_data.get_latest_fundamentals(db, stock_id)
    observed_fundamentals = backtest_core.fundamentals_to_observed(fundamentals_row)
    series = backtest_core.build_stock_series("", closes, observed_fundamentals, dates=dates)

    result = backtest_core.simulate(series, items, record_trades=True)
    baseline = backtest_core.buy_and_hold_return(series)

    return BacktestChartOut(
        points=[BacktestPointOut(date=d, close=c) for d, c in zip(dates, closes)],
        trades=[
            BacktestTradeOut(date=t["date"], action=t["action"], price=t["price"])
            for t in result["trade_events"]
        ],
        return_pct=result["return_pct"],
        buy_and_hold_return_pct=baseline,
        warmup_days=backtest_core.WARMUP_DAYS,
    )


@router.get("", response_model=list[EvaluationOut])
async def evaluation_history(
    stock_id: uuid.UUID | None = None,
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Evaluation).options(selectinload(Evaluation.details))
        .where(Evaluation.user_id == user.id)
        .order_by(Evaluation.run_at.desc()).limit(limit)
    )
    if stock_id is not None:
        query = query.where(Evaluation.stock_id == stock_id)
    return (await db.execute(query)).scalars().all()
