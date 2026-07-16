import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Evaluation, User, WatchlistItem
from app.schemas.common import EvaluationSummaryOut, WatchlistItemIn, WatchlistItemOut
from app.security import get_current_user
from app.services import market_data

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemOut])
async def list_watchlist(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    items = (
        await db.execute(
            select(WatchlistItem)
            .options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.added_at.desc())
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
    item = WatchlistItem(
        user_id=user.id, stock_id=stock.id, notes=body.notes,
        target_buy_price=body.target_buy_price, target_sell_price=body.target_sell_price,
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
