import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Evaluation, Stock, User, WatchlistItem
from app.schemas.common import (
    EvaluationSummaryOut,
    NewsItemOut,
    TickerSearchResult,
    WatchlistItemIn,
    WatchlistItemOut,
    WatchlistReorderIn,
)
from app.security import get_current_user
from app.services import market_data

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/search", response_model=list[TickerSearchResult])
async def search_stocks(
    q: str = Query(min_length=1, max_length=50), user: User = Depends(get_current_user)
):
    """Pesquisa tickers por nome/símbolo (ex: 'apple' -> AAPL) para facilitar
    adicionar à watchlist sem saber o símbolo exato de cor."""
    return await market_data.search_tickers(q)


@router.get("/news", response_model=list[NewsItemOut])
async def watchlist_news(
    limit: int = Query(default=20, le=50),
    user: User = Depends(get_current_user),
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
    items.sort(key=lambda i: i["published_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items[:limit]


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
    out = []
    for item in items:
        latest = (
            await db.execute(
                select(Evaluation)
                .where(Evaluation.user_id == user.id, Evaluation.stock_id == item.stock_id)
                .order_by(Evaluation.run_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        dto = WatchlistItemOut.model_validate(item)
        dto.latest_evaluation = EvaluationSummaryOut.model_validate(latest) if latest else None
        out.append(dto)
    return out


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
    user: User = Depends(get_current_user),
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
    item = (
        await db.execute(
            select(WatchlistItem).options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.id == item.id)
        )
    ).scalar_one()
    return WatchlistItemOut.model_validate(item)


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
