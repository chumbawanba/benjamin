import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Position, User
from app.schemas.common import PositionIn, PositionOut, PositionUpdateIn, StockOut
from app.security import get_current_user
from app.services import market_data

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


async def _to_dto(db: AsyncSession, position: Position) -> PositionOut:
    """Junta a posição guardada (quantidade + custo médio) ao preço atual para
    calcular valor de mercado e P&L não realizado — nada disto fica gravado,
    é recalculado a cada pedido a partir do último PriceSnapshot conhecido."""
    last_price, price_change_pct = await market_data.get_price_change(db, position.stock_id)
    cost_total = position.quantity * position.avg_cost
    market_value = (position.quantity * last_price) if last_price is not None else None
    unrealized_pl = (market_value - cost_total) if market_value is not None else None
    unrealized_pl_pct = (
        (unrealized_pl / cost_total * 100) if unrealized_pl is not None and cost_total != 0 else None
    )
    return PositionOut(
        id=position.id, stock=StockOut.model_validate(position.stock),
        quantity=position.quantity, avg_cost=position.avg_cost,
        cost_total=cost_total, last_price=last_price, price_change_pct=price_change_pct, market_value=market_value,
        unrealized_pl=unrealized_pl, unrealized_pl_pct=unrealized_pl_pct, updated_at=position.updated_at,
    )


@router.get("", response_model=list[PositionOut])
async def list_positions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    positions = (
        await db.execute(
            select(Position).options(selectinload(Position.stock))
            .where(Position.user_id == user.id)
            .order_by(Position.created_at.asc())
        )
    ).scalars().all()
    return [await _to_dto(db, p) for p in positions]


@router.post("", response_model=PositionOut, status_code=201)
async def create_position(
    body: PositionIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    stock = await market_data.validate_and_create_stock(db, body.ticker)
    if stock is None:
        raise HTTPException(status_code=422, detail=f"Ticker '{body.ticker}' não encontrado")
    dup = (
        await db.execute(select(Position).where(
            Position.user_id == user.id, Position.stock_id == stock.id
        ))
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=422, detail="Já tens uma posição nesta ação — edita a existente em vez de duplicar."
        )
    position = Position(
        user_id=user.id, stock_id=stock.id, quantity=body.quantity, avg_cost=body.avg_cost,
    )
    db.add(position)
    await db.commit()
    position = (
        await db.execute(
            select(Position).options(selectinload(Position.stock)).where(Position.id == position.id)
        )
    ).scalar_one()
    return await _to_dto(db, position)


@router.put("/{position_id}", response_model=PositionOut)
async def update_position(
    position_id: uuid.UUID, body: PositionUpdateIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    position = (
        await db.execute(
            select(Position).options(selectinload(Position.stock))
            .where(Position.id == position_id, Position.user_id == user.id)
        )
    ).scalar_one_or_none()
    if position is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    position.quantity = body.quantity
    position.avg_cost = body.avg_cost
    await db.commit()
    return await _to_dto(db, position)


@router.delete("/{position_id}", status_code=204)
async def delete_position(
    position_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    position = (
        await db.execute(select(Position).where(
            Position.id == position_id, Position.user_id == user.id
        ))
    ).scalar_one_or_none()
    if position is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    await db.delete(position)
    await db.commit()
