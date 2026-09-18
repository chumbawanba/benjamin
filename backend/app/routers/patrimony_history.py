import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PatrimonySnapshot, User
from app.schemas.common import (
    PatrimonyCurrentTotalsOut, PatrimonySnapshotIn, PatrimonySnapshotOut,
)
from app.security import get_current_user
from app.services import patrimony_history as patrimony_history_service

router = APIRouter(prefix="/patrimony-history", tags=["patrimony-history"])


def _to_dto(snap: PatrimonySnapshot) -> PatrimonySnapshotOut:
    net_worth = snap.stocks_value + snap.cash_value + snap.other_assets_value - snap.loans_balance
    return PatrimonySnapshotOut(
        id=snap.id, date=snap.date, currency=snap.currency,
        stocks_value=snap.stocks_value, cash_value=snap.cash_value,
        other_assets_value=snap.other_assets_value, loans_balance=snap.loans_balance,
        net_worth=net_worth, note=snap.note, updated_at=snap.updated_at,
    )


@router.get("", response_model=list[PatrimonySnapshotOut])
async def list_patrimony_history(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    snapshots = (
        await db.execute(
            select(PatrimonySnapshot)
            .where(PatrimonySnapshot.user_id == user.id)
            .order_by(PatrimonySnapshot.date.asc())
        )
    ).scalars().all()
    return [_to_dto(s) for s in snapshots]


@router.get("/current-totals", response_model=PatrimonyCurrentTotalsOut)
async def get_current_totals(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await patrimony_history_service.current_totals(db, user)


@router.post("", response_model=PatrimonySnapshotOut, status_code=200)
async def upsert_patrimony_snapshot(
    body: PatrimonySnapshotIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    # Upsert por data - uma nova entrada para uma data já existente substitui
    # a anterior (nunca há duas fotografias no mesmo dia, ver docstring do
    # modelo). Diferente de OtherAsset/Loan: aqui o "criar" e o "editar" são
    # a mesma operação do ponto de vista do utilizador ("diz-me o que tinhas
    # nesta data"), por isso um único endpoint em vez de POST + PUT.
    existing = (
        await db.execute(
            select(PatrimonySnapshot).where(
                PatrimonySnapshot.user_id == user.id, PatrimonySnapshot.date == body.date,
            )
        )
    ).scalar_one_or_none()
    currency = body.currency.upper().strip()
    note = body.note.strip() if body.note else None
    if existing is not None:
        existing.currency = currency
        existing.stocks_value = body.stocks_value
        existing.cash_value = body.cash_value
        existing.other_assets_value = body.other_assets_value
        existing.loans_balance = body.loans_balance
        existing.note = note
        snap = existing
    else:
        snap = PatrimonySnapshot(
            user_id=user.id, date=body.date, currency=currency,
            stocks_value=body.stocks_value, cash_value=body.cash_value,
            other_assets_value=body.other_assets_value, loans_balance=body.loans_balance,
            note=note,
        )
        db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return _to_dto(snap)


@router.delete("/{snapshot_id}", status_code=204)
async def delete_patrimony_snapshot(
    snapshot_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    snap = (
        await db.execute(
            select(PatrimonySnapshot).where(
                PatrimonySnapshot.id == snapshot_id, PatrimonySnapshot.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if snap is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    await db.delete(snap)
    await db.commit()
