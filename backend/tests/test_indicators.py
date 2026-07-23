"""Testes de app/services/indicators.py — foco no bug de cache stale corrigido
em 2026-07-24: indicadores "price" deixaram de ser cacheados por dia civil
(ver indicators.py::get_indicator). Bug real encontrado ao comparar valores
da app com o Yahoo Finance: a MSFT mostrava PRICE_CLOSE preso no valor da
manhã mesmo com o preço já a refletir uma queda de ~4% no dia."""
from decimal import Decimal

from sqlalchemy import select

from app.models import IndicatorValue, PriceSnapshot
from app.services import indicators


async def test_price_indicator_reflects_latest_price_without_caching(db_session, seeded_stock):
    """PRICE_CLOSE não deve ficar preso no valor da 1ª chamada do dia - o
    preço intradiário é atualizado a cada 15min (ensure_fresh/
    _record_latest_quote em market_data.py), e o indicador tem de refletir
    isso em cada pedido, não só uma vez por dia civil."""
    first = await indicators.get_indicator(db_session, seeded_stock.id, "PRICE_CLOSE")
    assert first == 180.0  # último close sintético do fixture seeded_stock

    latest_row = (
        await db_session.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.stock_id == seeded_stock.id)
            .order_by(PriceSnapshot.date.desc())
            .limit(1)
        )
    ).scalar_one()
    latest_row.close = Decimal("999.0")  # simula update intradiário do preço
    await db_session.commit()

    second = await indicators.get_indicator(db_session, seeded_stock.id, "PRICE_CLOSE")
    assert second == 999.0  # sem cache, reflete já o preço atualizado

    cached_rows = (
        await db_session.execute(
            select(IndicatorValue).where(
                IndicatorValue.stock_id == seeded_stock.id,
                IndicatorValue.indicator_name == "PRICE_CLOSE",
            )
        )
    ).scalars().all()
    assert cached_rows == []  # indicadores "price" nunca ficam gravados em indicator_values


async def test_fundamental_indicator_still_cached_per_day(db_session, seeded_stock):
    """Ao contrário dos indicadores "price", os "fundamental" continuam
    cacheados por dia civil - só mudam a cada refresh_fundamentals (cooldown
    de horas), por isso o cache diário não introduz staleness relevante aqui
    e não há razão para o remover."""
    value = await indicators.get_indicator(db_session, seeded_stock.id, "PE_RATIO")
    assert value == 12.0

    cached = (
        await db_session.execute(
            select(IndicatorValue).where(
                IndicatorValue.stock_id == seeded_stock.id,
                IndicatorValue.indicator_name == "PE_RATIO",
            )
        )
    ).scalar_one_or_none()
    assert cached is not None
    assert float(cached.value) == 12.0
