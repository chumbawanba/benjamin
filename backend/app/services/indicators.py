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
    """Devolve o valor atual do indicador.

    Indicadores "price" (PRICE_CLOSE, RSI_14, SMA_50/200, PRICE_VS_SMA_50/200)
    NUNCA são cacheados - são recalculados a cada pedido a partir do
    PriceSnapshot mais recente (leitura de BD + pandas, sem custo de API
    externa, por isso cachear não poupava nada). Bug real corrigido em
    2026-07-24: com o cache diário antigo (indicator_values, 1 valor por dia
    civil), o preço no topo da StockDetail (get_price_change, sempre fresco)
    ficava dessincronizado do RSI/SMA/PRICE_CLOSE mostrados a seguir - o
    preço intradiário atualiza a cada 15min (ensure_fresh/_record_latest_quote)
    mas o indicador ficava preso no valor da primeira vez que foi calculado
    nesse dia, até à meia-noite UTC. Confirmado ao comparar com o Yahoo
    Finance: a MSFT mostrava PRICE_CLOSE=397.75 (valor da manhã) com o preço
    já em 381.58 (-4% no dia), e PRICE_VS_SMA_50/200 saíam também errados por
    arrasto (calculados com o close desatualizado).

    Indicadores "fundamental" (P/E, ROE, margens, etc.) continuam cacheados
    em indicator_values por dia civil - só mudam a cada refresh_fundamentals
    (cooldown de horas), por isso o cache diário não introduz staleness
    relevante aqui."""
    if metric not in INDICATORS:
        raise ValueError(f"Indicador desconhecido: {metric}")
    spec = INDICATORS[metric]

    if spec["kind"] == "price":
        closes = await _load_closes(db, stock_id)
        return spec["fn"](closes)

    today = datetime.now(timezone.utc).date()
    cached = (
        await db.execute(select(IndicatorValue).where(
            IndicatorValue.stock_id == stock_id,
            IndicatorValue.indicator_name == metric,
            IndicatorValue.date == today,
        ))
    ).scalar_one_or_none()
    # Só confiamos na cache quando tem valor. Um cache com None guardado antes
    # de existirem dados de mercado (ex: primeira tentativa falhou) não deve
    # bloquear recalculos posteriores no mesmo dia, uma vez que os dados podem
    # ter chegado entretanto (ensure_fresh corre sempre antes disto).
    if cached is not None and cached.value is not None:
        return float(cached.value)

    value = await _load_fundamental(db, stock_id, spec["field"])
    if value is not None and spec.get("scale"):
        value = value / spec["scale"]

    decimal_value = Decimal(str(round(value, 6))) if value is not None else None
    if cached is not None:
        cached.value = decimal_value
    else:
        db.add(IndicatorValue(
            stock_id=stock_id, indicator_name=metric, date=today, value=decimal_value,
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
