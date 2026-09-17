"""Projeção de património líquido a longo prazo (fase pedida pelo Edgar depois
dos Empréstimos - ver ESTADO.md secção 11).

Extrapola o valor atual do portfolio a uma rentabilidade anual **assumida**
(input do utilizador, não calculada a partir do histórico de preços - mantém
o pressuposto explícito e a projeção simples de perceber) e reduz o saldo de
cada empréstimo linearmente pela sua prestação mensal (prestação x 12 por
ano, sem separar juro/capital - ver CLAUDE.md, decisão tomada com o Edgar:
"linear pela prestação" em vez de amortização real). Empréstimos sem
prestação registada mantêm o saldo constante ao longo da projeção, porque não
há como saber o plano de pagamento.

Não é um modelo actuarial: não simula inflação, não muda a taxa de câmbio ao
longo do tempo (usa a taxa atual, fixa, para todos os anos) e não tem em conta
novas entradas/saídas de capital - é uma extrapolação simples dos dados
actuais, para dar uma ideia de tendência, não uma previsão financeira.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Loan, Position, User
from app.schemas.common import ProjectionOut, ProjectionPointOut
from app.services import fx, market_data


async def _current_portfolio_value(db: AsyncSession, user: User, target: str) -> Decimal:
    positions = (
        await db.execute(
            select(Position).options(selectinload(Position.stock)).where(Position.user_id == user.id)
        )
    ).scalars().all()
    total = Decimal("0")
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
        total += value
    return total


async def _current_loans(db: AsyncSession, user: User, target: str) -> list[tuple[Decimal, Decimal]]:
    """Devolve uma lista de (saldo_convertido, prestação_anual_convertida) - um
    par por empréstimo. Prestação = 0 quando não registada (saldo desse
    empréstimo fica constante na projeção)."""
    loans = (await db.execute(select(Loan).where(Loan.user_id == user.id))).scalars().all()
    result: list[tuple[Decimal, Decimal]] = []
    for loan in loans:
        rate = await fx.get_rate(db, loan.currency, target)
        if rate is None:
            continue
        balance = loan.balance * rate
        annual_payment = (loan.monthly_payment * Decimal("12") * rate) if loan.monthly_payment else Decimal("0")
        result.append((balance, annual_payment))
    return result


async def compute(db: AsyncSession, user: User, years: int, annual_return_pct: Decimal) -> ProjectionOut:
    target = user.preferred_currency
    portfolio_value = await _current_portfolio_value(db, user, target)
    loans = await _current_loans(db, user, target)
    starting_loans_balance = sum((balance for balance, _ in loans), Decimal("0"))

    growth_factor = Decimal("1") + (annual_return_pct / Decimal("100"))
    balances = [balance for balance, _ in loans]
    payments = [payment for _, payment in loans]

    points: list[ProjectionPointOut] = []
    for year in range(years + 1):
        pv = portfolio_value * (growth_factor ** year)
        if year > 0:
            balances = [max(Decimal("0"), b - p) for b, p in zip(balances, payments)]
        loans_total = sum(balances, Decimal("0"))
        points.append(ProjectionPointOut(
            year=year, portfolio_value=pv, loans_balance=loans_total, net_worth=pv - loans_total,
        ))

    return ProjectionOut(
        currency=target, annual_return_pct=annual_return_pct, years=years,
        starting_portfolio_value=portfolio_value, starting_loans_balance=starting_loans_balance,
        points=points,
    )
