import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Evaluation, FundamentalsSnapshot, Stock, StrategyItem, StrategyTemplate, User, WatchlistItem,
)
from app.schemas.common import (
    CategorySynthesisOut,
    EvaluationCriterionOut,
    EvaluationSummaryOut,
    FundamentalsOut,
    IndicatorValueOut,
    NewsItemOut,
    PricePointOut,
    StockDetailOut,
    StockOut,
    StockSynthesisOut,
    SuggestionOut,
    TickerSearchResult,
    WatchlistItemIn,
    WatchlistItemOut,
    WatchlistReorderIn,
)
from app.security import get_current_user
from app.services import agent, indicators, market_data, synthesis
from app.services.rate_limit import rate_limit_user
from app.services.indicators_core import INDICATORS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _rolling_sma(period: int, closes: list[Decimal | None]) -> list[float | None]:
    """Média móvel simples causal (só olha para trás), vetorizada com pandas —
    usada para desenhar a linha SMA_200 no gráfico da StockDetail. Mesma
    técnica do otimizador (backtest_core.py): rolling().mean() dá o mesmo
    resultado que recalcular dia a dia, mas em O(n) em vez de O(n²)."""
    s = pd.Series([float(c) if c is not None else None for c in closes], dtype=float)
    rolling = s.rolling(period).mean()
    return [None if pd.isna(v) else float(v) for v in rolling]


async def _to_dto(db: AsyncSession, user_id: uuid.UUID, item: WatchlistItem) -> WatchlistItemOut:
    """Constrói o WatchlistItemOut com última avaliação + variação de preço.
    Partilhado entre list_watchlist e add_to_watchlist (que devolve o item já
    com a avaliação automática feita)."""
    latest = (
        await db.execute(
            select(Evaluation)
            .where(Evaluation.user_id == user_id, Evaluation.stock_id == item.stock_id)
            .order_by(Evaluation.run_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    dto = WatchlistItemOut.model_validate(item)
    dto.latest_evaluation = EvaluationSummaryOut.model_validate(latest) if latest else None
    dto.last_price, dto.price_change_pct = await market_data.get_price_change(db, item.stock_id)
    return dto


@router.get("/search", response_model=list[TickerSearchResult])
async def search_stocks(
    q: str = Query(min_length=1, max_length=50),
    user: User = Depends(rate_limit_user("watchlist_search", max_calls=30, window_seconds=60)),
):
    """Pesquisa tickers por nome/símbolo (ex: 'apple' -> AAPL) para facilitar
    adicionar à watchlist sem saber o símbolo exato de cor."""
    return await market_data.search_tickers(q)


@router.get("/news", response_model=list[NewsItemOut])
async def watchlist_news(
    limit: int = Query(default=20, le=50),
    user: User = Depends(rate_limit_user("watchlist_news", max_calls=10, window_seconds=300)),
    db: AsyncSession = Depends(get_db),
):
    """Notícias recentes das ações da watchlist, agregadas e ordenadas por
    data (mais recentes primeiro). Usado no separador "Notícias" da Overview."""
    tickers = (
        await db.execute(
            select(Stock.ticker)
            .join(WatchlistItem, WatchlistItem.stock_id == Stock.id)
            .where(WatchlistItem.user_id == user.id)
        )
    ).scalars().all()
    if not tickers:
        return []
    results = await asyncio.gather(*(market_data.get_company_news(t) for t in tickers))
    items = [item for group in results for item in group if item.get("headline")]

    # A mesma notícia (ex: "mercado em queda hoje") costuma vir repetida para
    # vários tickers — a Finnhub devolve-a em cada /company-news relevante.
    # Dedup por url (fallback: headline) mantendo a primeira ocorrência.
    seen: set[str] = set()
    deduped = []
    for item in items:
        key = item.get("url") or item.get("headline")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda i: i["published_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return deduped[:limit]


@router.get("/suggestions", response_model=list[SuggestionOut])
async def watchlist_suggestions(
    limit: int = Query(default=8, le=20),
    user: User = Depends(rate_limit_user("watchlist_suggestions", max_calls=10, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
):
    """Sugestões de novas ações "parecidas" (mesma indústria, via Finnhub
    /stock/peers) com as que já estão na watchlist do utilizador — outra
    forma de descobrir ações além da pesquisa manual por nome/símbolo.
    Exclui sugestões que já estão na watchlist; para cada ticker sugerido
    indica-se o `based_on` (ticker da watchlist que originou a sugestão)."""
    tickers = (
        await db.execute(
            select(Stock.ticker)
            .join(WatchlistItem, WatchlistItem.stock_id == Stock.id)
            .where(WatchlistItem.user_id == user.id)
        )
    ).scalars().all()
    if not tickers:
        return []
    existing = {t.upper() for t in tickers}
    results = await asyncio.gather(*(market_data.get_peers(t) for t in tickers))

    suggestions: list[SuggestionOut] = []
    seen: set[str] = set()
    for source_ticker, peers in zip(tickers, results):
        for peer in peers:
            if peer in existing or peer in seen:
                continue
            seen.add(peer)
            suggestions.append(SuggestionOut(ticker=peer, based_on=source_ticker))
            if len(suggestions) >= limit:
                return suggestions
    return suggestions


@router.get("", response_model=list[WatchlistItemOut])
async def list_watchlist(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    items = (
        await db.execute(
            select(WatchlistItem)
            .options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.display_order.asc(), WatchlistItem.added_at.desc())
        )
    ).scalars().all()
    return [await _to_dto(db, user.id, item) for item in items]


@router.get("/{item_id}/detail", response_model=StockDetailOut)
async def watchlist_item_detail(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detalhe de uma ação da watchlist: histórico de preço, todos os
    indicadores atuais, fundamentais e o critério-a-critério da última
    avaliação. Usado na página StockDetail (drill-down a partir de um ticker)."""
    item = (
        await db.execute(
            select(WatchlistItem).options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.id == item_id, WatchlistItem.user_id == user.id)
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Não encontrado")

    stock = item.stock
    await market_data.ensure_fresh(db, stock)

    last_price, price_change_pct = await market_data.get_price_change(db, stock.id)
    # 365 dias (máximo guardado pelo backfill) para dar espaço a uma SMA_200
    # com histórico suficiente — com menos dias a média fica sempre None.
    history_rows = await market_data.get_price_history(db, stock.id, days=365)
    sma_200_series = _rolling_sma(200, [r.close for r in history_rows])
    price_history = [
        PricePointOut(date=r.date, close=r.close, sma_200=sma)
        for r, sma in zip(history_rows, sma_200_series)
    ]

    indicator_values = [
        IndicatorValueOut(
            key=key, value=await indicators.get_indicator(db, stock.id, key),
            description=spec.get("description"),
        )
        for key, spec in INDICATORS.items()
    ]
    # Reaproveita os valores já calculados acima - sem pedidos extra à BD.
    synthesis_result = synthesis.compute_synthesis({iv.key: iv.value for iv in indicator_values})

    fundamentals_row = (
        await db.execute(
            select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock.id)
            .order_by(FundamentalsSnapshot.date.desc()).limit(1)
        )
    ).scalar_one_or_none()
    fundamentals = FundamentalsOut.model_validate(fundamentals_row) if fundamentals_row else None

    latest_eval = (
        await db.execute(
            select(Evaluation).options(selectinload(Evaluation.details))
            .where(Evaluation.user_id == user.id, Evaluation.stock_id == stock.id)
            .order_by(Evaluation.run_at.desc()).limit(1)
        )
    ).scalar_one_or_none()

    strategy_name = None
    criteria: list[EvaluationCriterionOut] = []
    if latest_eval is not None:
        template = (
            await db.execute(
                select(StrategyTemplate).where(StrategyTemplate.id == latest_eval.strategy_template_id)
            )
        ).scalar_one_or_none()
        strategy_name = template.name if template else None

        item_ids = [d.strategy_item_id for d in latest_eval.details]
        strategy_items = (
            await db.execute(select(StrategyItem).where(StrategyItem.id.in_(item_ids)))
        ).scalars().all()
        items_by_id = {si.id: si for si in strategy_items}
        for d in latest_eval.details:
            si = items_by_id.get(d.strategy_item_id)
            if si is None:
                continue
            criteria.append(EvaluationCriterionOut(
                name=si.name, metric=si.metric, operator=si.operator,
                threshold_value=si.threshold_value, threshold_value_max=si.threshold_value_max,
                weight=si.weight, direction=si.direction,
                observed_value=d.observed_value, passed=d.passed, contribution=d.contribution,
            ))

    await db.commit()  # ensure_fresh/get_indicator podem ter gravado cache novo

    return StockDetailOut(
        stock=StockOut.model_validate(stock),
        last_price=last_price, price_change_pct=price_change_pct,
        price_history=price_history,
        indicators=indicator_values,
        fundamentals=fundamentals,
        latest_evaluation=EvaluationSummaryOut.model_validate(latest_eval) if latest_eval else None,
        strategy_name=strategy_name,
        criteria=criteria,
        synthesis=StockSynthesisOut(
            score=synthesis_result.score,
            categories=[
                CategorySynthesisOut(
                    category=c.category, label=c.label,
                    classification=c.classification, reason=c.reason,
                )
                for c in synthesis_result.categories
            ],
        ),
    )


@router.put("/reorder", status_code=204)
async def reorder_watchlist(
    body: WatchlistReorderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grava a nova ordem manual da watchlist (usado na página Overview, via
    as setas ▲▼ no separador "Sinais"). `ordered_ids` deve conter os ids de
    todos os itens do utilizador; ids em falta ou de outro utilizador são
    ignorados."""
    owned_ids = set(
        (
            await db.execute(
                select(WatchlistItem.id).where(WatchlistItem.user_id == user.id)
            )
        ).scalars().all()
    )
    for index, item_id in enumerate(body.ordered_ids):
        if item_id not in owned_ids:
            continue
        await db.execute(
            WatchlistItem.__table__.update()
            .where(WatchlistItem.id == item_id)
            .values(display_order=index)
        )
    await db.commit()


@router.post("", response_model=WatchlistItemOut, status_code=201)
async def add_to_watchlist(
    body: WatchlistItemIn,
    user: User = Depends(rate_limit_user("watchlist_add", max_calls=20, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
):
    stock = await market_data.validate_and_create_stock(db, body.ticker)
    if stock is None:
        raise HTTPException(status_code=422, detail=f"Ticker '{body.ticker}' não encontrado")
    dup = (
        await db.execute(select(WatchlistItem).where(
            WatchlistItem.user_id == user.id, WatchlistItem.stock_id == stock.id
        ))
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=422, detail="Ação já está na watchlist")
    max_order = (
        await db.execute(
            select(func.max(WatchlistItem.display_order)).where(WatchlistItem.user_id == user.id)
        )
    ).scalar()
    next_order = (max_order + 1) if max_order is not None else 0
    item = WatchlistItem(
        user_id=user.id, stock_id=stock.id, notes=body.notes,
        target_buy_price=body.target_buy_price, target_sell_price=body.target_sell_price,
        display_order=next_order,
    )
    db.add(item)
    await db.commit()

    # Avalia já com as estratégias ativas do utilizador — sem isto a ação
    # ficava com "Buy 0 / Sell 0" sem contexto até alguém correr o Feed
    # manualmente, o que parece um bug a quem acabou de a adicionar.
    templates = (
        await db.execute(
            select(StrategyTemplate).where(
                StrategyTemplate.user_id == user.id, StrategyTemplate.is_active.is_(True)
            )
        )
    ).scalars().all()
    for template in templates:
        try:
            await agent.evaluate(db, stock.id, template.id, user.id)
        except Exception:
            logger.exception(
                "Falha ao avaliar %s / %s logo após adicionar à watchlist", stock.ticker, template.name
            )
    await db.commit()

    item = (
        await db.execute(
            select(WatchlistItem).options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.id == item.id)
        )
    ).scalar_one()
    return await _to_dto(db, user.id, item)


@router.delete("/{item_id}", status_code=204)
async def remove_from_watchlist(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(select(WatchlistItem).where(
            WatchlistItem.id == item_id, WatchlistItem.user_id == user.id
        ))
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    await db.delete(item)
    await db.commit()
