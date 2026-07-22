from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models import FxRateSnapshot
from app.services import fx


async def test_get_rate_same_currency_is_one_without_api_call(db_session):
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"rate": "0.5"})) as mocked:
        rate = await fx.get_rate(db_session, "eur", "EUR")
    assert rate == Decimal("1")
    mocked.assert_not_called()


async def test_get_rate_calls_twelvedata_and_caches(db_session):
    mocked = AsyncMock(return_value={"rate": "0.92"})
    with patch("app.services.market_data._twelvedata_get", new=mocked):
        rate1 = await fx.get_rate(db_session, "USD", "EUR")
        rate2 = await fx.get_rate(db_session, "USD", "EUR")
    assert rate1 == Decimal("0.92")
    assert rate2 == Decimal("0.92")
    # segunda chamada usou o cache (FxRateSnapshot de hoje), não voltou à API
    assert mocked.await_count == 1

    rows = (await db_session.execute(select(FxRateSnapshot))).scalars().all()
    assert len(rows) == 1
    assert rows[0].base_currency == "USD"
    assert rows[0].quote_currency == "EUR"


async def test_get_rate_falls_back_to_stale_cache_on_api_failure(db_session):
    from datetime import date, timedelta
    stale = FxRateSnapshot(
        base_currency="USD", quote_currency="EUR",
        date=date.today() - timedelta(days=30), rate=Decimal("0.87"),
    )
    db_session.add(stale)
    await db_session.commit()

    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=Exception("boom"))):
        rate = await fx.get_rate(db_session, "USD", "EUR")
    assert rate == Decimal("0.87")


async def test_get_rate_returns_none_without_cache_or_api(db_session):
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=Exception("boom"))):
        rate = await fx.get_rate(db_session, "USD", "GBP")
    assert rate is None
