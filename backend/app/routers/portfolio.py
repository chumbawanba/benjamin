import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import FxRateSnapshot, Position, Stock, User
from app.schemas.common import (
    FxRateOut, PortfolioCurrencyIn, PortfolioCurrencyOut, PositionIn, PositionOut, PositionUpdateIn, StockOut,
)
from app.security import get_current_user
from app.services import fx, market_data

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


async def _to_dto(
    db: AsyncSession, position: Position, target_currency: str, rate: Decimal | None,
) -> PositionOut:
    """Junta a posição guardada (quantidade + custo médio) ao preço atual para
    calcular valor de mercado e P&L não realizado — nada disto fica gravado,
    é recalculado a cada pedido a partir do último PriceSnapshot conhecido.

    `rate` é a taxa de câmbio da moeda da ação para `target_currency`, já
    resolvida pelo chamador (list_positions resolve uma vez por moeda distinta
    em vez de uma vez por posição — evita pedidos repetidos à Twelve Data)."""
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
        display_currency=target_currency,
        cost_total_converted=(cost_total * rate) if rate is not None else None,
        market_value_converted=(market_value * rate) if market_value is not None and rate is not None else None,
        unrealized_pl_converted=(unrealized_pl * rate) if unrealized_pl is not None and rate is not None else None,
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
    # Garante que cada ação tem preço/fundamentais atuais - sem isto, uma
    # posição criada diretamente no portfolio (fora da watchlist, onde
    # add_to_watchlist/agent.evaluate já chamam ensure_fresh) ficava para
    # sempre sem PriceSnapshot, logo sem Valor/P&L (só "—"). Gratuito na
    # maior parte dos pedidos: ensure_fresh sai logo se já houver um
    # snapshot com menos de FRESHNESS_DAYS.
    for p in positions:
        await market_data.ensure_fresh(db, p.stock)
    target = user.preferred_currency
    # Uma taxa por moeda distinta presente no portfolio, não uma por posição.
    rates: dict[str, Decimal | None] = {}
    for p in positions:
        currency = p.stock.currency
        if currency and currency not in rates:
            rates[currency] = await fx.get_rate(db, currency, target)
    result = [
        await _to_dto(db, p, target, rates.get(p.stock.currency) if p.stock.currency else None)
        for p in positions
    ]
    await db.commit()  # ensure_fresh/get_rate podem ter gravado cache novo
    return result


@router.get("/currency", response_model=PortfolioCurrencyOut)
async def get_currency(user: User = Depends(get_current_user)):
    return PortfolioCurrencyOut(currency=user.preferred_currency)


@router.put("/currency", response_model=PortfolioCurrencyOut)
async def set_currency(
    body: PortfolioCurrencyIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    user.preferred_currency = body.currency.upper().strip()
    await db.commit()
    return PortfolioCurrencyOut(currency=user.preferred_currency)


@router.get("/fx-rates", response_model=list[FxRateOut])
async def list_fx_rates(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Taxas de câmbio atualmente usadas para converter o portfolio - só as
    moedas das ações que o utilizador realmente tem, contra a moeda preferida
    (mesmas que list_positions usa, ver _to_dto). Serve de referência para o
    utilizador consultar em caso de dúvida sobre um valor convertido."""
    target = user.preferred_currency
    currencies = (
        await db.execute(
            select(Stock.currency).join(Position, Position.stock_id == Stock.id)
            .where(Position.user_id == user.id, Stock.currency.is_not(None))
            .distinct()
        )
    ).scalars().all()

    today = datetime.now(timezone.utc).date()
    results = []
    for currency in currencies:
        if currency == target:
            continue
        rate = await fx.get_rate(db, currency, target)
        if rate is None:
            continue
        snapshot = (
            await db.execute(
                select(FxRateSnapshot)
                .where(FxRateSnapshot.base_currency == currency, FxRateSnapshot.quote_currency == target)
                .order_by(FxRateSnapshot.date.desc()).limit(1)
            )
        ).scalar_one_or_none()
        results.append(FxRateOut(
            base_currency=currency, quote_currency=target, rate=rate,
            date=snapshot.date if snapshot else today,
        ))
    return results


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
    # Sem isto, uma ação nova (ainda sem watchlist/avaliação) ficava sem
    # nenhum PriceSnapshot até alguém a adicionar também à watchlist.
    await market_data.ensure_fresh(db, stock)
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
    target = user.preferred_currency
    rate = await fx.get_rate(db, stock.currency, target) if stock.currency else None
    return await _to_dto(db, position, target, rate)


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
    target = user.preferred_currency
    rate = await fx.get_rate(db, position.stock.currency, target) if position.stock.currency else None
    return await _to_dto(db, position, target, rate)


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
