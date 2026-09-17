import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import OtherAsset, User
from app.schemas.common import (
    VALID_OTHER_ASSET_CATEGORIES, OtherAssetIn, OtherAssetOut, OtherAssetUpdateIn,
)
from app.security import get_current_user
from app.services import fx

router = APIRouter(prefix="/other-assets", tags=["other-assets"])


def _to_dto(asset: OtherAsset, target_currency: str, rate: Decimal | None) -> OtherAssetOut:
    return OtherAssetOut(
        id=asset.id, category=asset.category, name=asset.name, currency=asset.currency, value=asset.value,
        expected_return_pct=asset.expected_return_pct, updated_at=asset.updated_at,
        display_currency=target_currency,
        value_converted=(asset.value * rate) if rate is not None else None,
    )


@router.get("", response_model=list[OtherAssetOut])
async def list_other_assets(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    assets = (
        await db.execute(
            select(OtherAsset).where(OtherAsset.user_id == user.id).order_by(OtherAsset.created_at.asc())
        )
    ).scalars().all()
    target = user.preferred_currency
    # Uma taxa por moeda distinta, não uma por ativo (mesmo padrão de
    # list_positions/list_loans).
    rates: dict[str, Decimal | None] = {}
    for asset in assets:
        if asset.currency not in rates:
            rates[asset.currency] = await fx.get_rate(db, asset.currency, target)
    result = [_to_dto(asset, target, rates.get(asset.currency)) for asset in assets]
    await db.commit()  # fx.get_rate pode ter gravado cache novo
    return result


@router.post("", response_model=OtherAssetOut, status_code=201)
async def create_other_asset(
    body: OtherAssetIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if body.category not in VALID_OTHER_ASSET_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Categoria inválida: {body.category}")
    currency = body.currency.upper().strip()
    asset = OtherAsset(
        user_id=user.id, category=body.category, name=body.name.strip(), currency=currency, value=body.value,
        expected_return_pct=body.expected_return_pct,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    target = user.preferred_currency
    rate = await fx.get_rate(db, currency, target)
    await db.commit()  # fx.get_rate pode ter gravado cache novo
    return _to_dto(asset, target, rate)


@router.put("/{asset_id}", response_model=OtherAssetOut)
async def update_other_asset(
    asset_id: uuid.UUID, body: OtherAssetUpdateIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    asset = (
        await db.execute(select(OtherAsset).where(OtherAsset.id == asset_id, OtherAsset.user_id == user.id))
    ).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    asset.name = body.name.strip()
    asset.value = body.value
    asset.expected_return_pct = body.expected_return_pct
    await db.commit()
    target = user.preferred_currency
    rate = await fx.get_rate(db, asset.currency, target)
    await db.commit()
    return _to_dto(asset, target, rate)


@router.delete("/{asset_id}", status_code=204)
async def delete_other_asset(
    asset_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    asset = (
        await db.execute(select(OtherAsset).where(OtherAsset.id == asset_id, OtherAsset.user_id == user.id))
    ).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    await db.delete(asset)
    await db.commit()
