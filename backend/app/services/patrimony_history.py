"""Totais atuais de património, decompostos em stocks/cash/outros ativos/
dívida - usados para pré-preencher o formulário de uma nova fotografia do
histórico de património (PatrimonySnapshot) quando a data escolhida é hoje
(ver services/projection.py, de onde esta lógica de agregação foi adaptada -
a diferença aqui é separar stocks de cash em vez de somar tudo em
"portfolio_value", para o breakdown completo pedido pelo Edgar)."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Loan, OtherAsset, Position, User
from app.schemas.common import PatrimonyCurrentTotalsOut
from app.services import fx, market_data


async def current_totals(db: AsyncSession, user: User) -> PatrimonyCurrentTotalsOut:
    target = user.preferred_currency

    positions = (
        await db.execute(
            select(Position).options(selectinload(Position.stock)).where(Position.user_id == user.id)
        )
    ).scalars().all()
    stocks_value = Decimal("0")
    cash_value = Decimal("0")
    for p in positions:
        await market_data.ensure_fresh(db, p.stock)
        last_price, _ = await market_data.get_price_change(db, p.stock_id)
        if last_price is None:
            continue
        value = p.quantity * last_price
        if p.stock.currency and p.stock.currency != target:
            rate = await fx.get_rate(db, p.stock.currency, target)
            if rate is None:
                continue
            value = value * rate
        if p.stock.asset_type == "cash":
            cash_value += value
        else:
            stocks_value += value

    other_assets = (await db.execute(select(OtherAsset).where(OtherAsset.user_id == user.id))).scalars().all()
    other_assets_value = Decimal("0")
    for asset in other_assets:
        rate = await fx.get_rate(db, asset.currency, target)
        if rate is None:
            continue
        other_assets_value += asset.value * rate

    loans = (await db.execute(select(Loan).where(Loan.user_id == user.id))).scalars().all()
    loans_balance = Decimal("0")
    for loan in loans:
        rate = await fx.get_rate(db, loan.currency, target)
        if rate is None:
            continue
        loans_balance += loan.balance * rate

    return PatrimonyCurrentTotalsOut(
        currency=target,
        stocks_value=stocks_value,
        cash_value=cash_value,
        other_assets_value=other_assets_value,
        loans_balance=loans_balance,
    )
