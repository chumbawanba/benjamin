"""Camada de indicadores com BD: le snapshots, calcula via indicators_core, faz cache."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FundamentalsSnapshot, IndicatorValue, PriceSnapshot
from app.services.indicators_core import INDICATORS


async def get_indicator(db: AsyncSession, stock_id: uuid.UUID, metric: str) -> float | None:
    """Devolve o valor do indicador para hoje, usando cache em indicator_values."""
    if metric not in INDICATORS:
        raise ValueError(f"Indicador desconhecido: {metric}")
    today = datetime.now(timezone.utc).date()

    cached = (
        await db.execute(select(IndicatorValue).where(
            IndicatorValue.stock_id == stock_id,
            IndicatorValue.indicator_name == metric,
            IndicatorValue.date == today,
        ))
    ).scalar_one_or_none()
    if cached is not None:
        return float(cached.value) if cached.value is not None else None

    spec = INDICATORS[metric]
    if spec["kind"] == "price":
        closes = await _load_closes(db, stock_id)
        value = spec["fn"](closes)
    else:  # fundamental
        value = await _load_fundamental(db, stock_id, spec["field"])

    db.add(IndicatorValue(
        stock_id=stock_id, indicator_name=metric, date=today,
        value=Decimal(str(round(value, 6))) if value is not None else None,
    ))
    await db.flush()
    return value


async def _load_closes(db: AsyncSession, stock_id: uuid.UUID) -> pd.Series:
    rows = (
        await db.execute(
            select(PriceSnapshot.date, PriceSnapshot.close)
            .where(PriceSnapshot.stock_id == stock_id, PriceSnapshot.close.is_not(None))
            .order_by(PriceSnapshot.date.asc())
        )
    ).all()
    return pd.Series([float(r.close) for r in rows], dtype=float)


async def _load_fundamental(db: AsyncSession, stock_id: uuid.UUID, field: str) -> float | None:
    row = (
        await db.execute(
            select(FundamentalsSnapshot)
            .where(FundamentalsSnapshot.stock_id == stock_id)
            .order_by(FundamentalsSnapshot.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    value = getattr(row, field)
    return float(value) if value is not None else None
