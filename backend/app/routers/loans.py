import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Loan, User
from app.schemas.common import LoanIn, LoanOut, LoanUpdateIn
from app.security import get_current_user
from app.services import fx

router = APIRouter(prefix="/loans", tags=["loans"])


def _to_dto(loan: Loan, target_currency: str, rate: Decimal | None) -> LoanOut:
    return LoanOut(
        id=loan.id, name=loan.name, currency=loan.currency, balance=loan.balance,
        interest_rate=loan.interest_rate, monthly_payment=loan.monthly_payment,
        updated_at=loan.updated_at, display_currency=target_currency,
        balance_converted=(loan.balance * rate) if rate is not None else None,
    )


@router.get("", response_model=list[LoanOut])
async def list_loans(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    loans = (
        await db.execute(select(Loan).where(Loan.user_id == user.id).order_by(Loan.created_at.asc()))
    ).scalars().all()
    target = user.preferred_currency
    # Uma taxa por moeda distinta presente nos empréstimos, não uma por empréstimo
    # (mesmo padrão de list_positions em routers/portfolio.py).
    rates: dict[str, Decimal | None] = {}
    for loan in loans:
        if loan.currency not in rates:
            rates[loan.currency] = await fx.get_rate(db, loan.currency, target)
    result = [_to_dto(loan, target, rates.get(loan.currency)) for loan in loans]
    await db.commit()  # fx.get_rate pode ter gravado cache novo
    return result


@router.post("", response_model=LoanOut, status_code=201)
async def create_loan(
    body: LoanIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    currency = body.currency.upper().strip()
    loan = Loan(
        user_id=user.id, name=body.name.strip(), currency=currency, balance=body.balance,
        interest_rate=body.interest_rate, monthly_payment=body.monthly_payment,
    )
    db.add(loan)
    await db.commit()
    await db.refresh(loan)
    target = user.preferred_currency
    rate = await fx.get_rate(db, currency, target)
    await db.commit()  # fx.get_rate pode ter gravado cache novo
    return _to_dto(loan, target, rate)


@router.put("/{loan_id}", response_model=LoanOut)
async def update_loan(
    loan_id: uuid.UUID, body: LoanUpdateIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    loan = (
        await db.execute(select(Loan).where(Loan.id == loan_id, Loan.user_id == user.id))
    ).scalar_one_or_none()
    if loan is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    loan.name = body.name.strip()
    loan.balance = body.balance
    loan.interest_rate = body.interest_rate
    loan.monthly_payment = body.monthly_payment
    await db.commit()
    target = user.preferred_currency
    rate = await fx.get_rate(db, loan.currency, target)
    await db.commit()
    return _to_dto(loan, target, rate)


@router.delete("/{loan_id}", status_code=204)
async def delete_loan(
    loan_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    loan = (
        await db.execute(select(Loan).where(Loan.id == loan_id, Loan.user_id == user.id))
    ).scalar_one_or_none()
    if loan is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    await db.delete(loan)
    await db.commit()
