"""Testes unitários para o backfill de perfil (nome/exchange/sector/currency)
em falta — cobre o caso em que a Finnhub estava indisponível/rate-limited no
momento em que a stock foi criada (ver validate_and_create_stock)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.models import PriceSnapshot, Stock
from app.services import market_data


async def test_backfill_profile_fills_missing_name(db_session):
    stock = Stock(ticker="MSFT")  # simula stock criada sem metadados
    db_session.add(stock)
    await db_session.flush()

    profile = {"name": "Microsoft Corp", "currency": "USD", "exchange": "NASDAQ", "finnhubIndustry": "Technology"}
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=profile)):
        await market_data._backfill_profile(db_session, stock)

    assert stock.name == "Microsoft Corp"
    assert stock.currency == "USD"
    assert stock.exchange == "NASDAQ"
    assert stock.sector == "Technology"


async def test_backfill_profile_skips_when_name_already_set(db_session):
    stock = Stock(ticker="AAPL", name="Apple Inc.")
    db_session.add(stock)
    await db_session.flush()

    mock = AsyncMock(return_value={"name": "outro nome"})
    with patch("app.services.market_data._finnhub_get", new=mock):
        await market_data._backfill_profile(db_session, stock)

    mock.assert_not_called()
    assert stock.name == "Apple Inc."  # inalterado


async def test_backfill_profile_survives_finnhub_failure(db_session):
    stock = Stock(ticker="TSLA")
    db_session.add(stock)
    await db_session.flush()

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=Exception("429"))):
        await market_data._backfill_profile(db_session, stock)  # não deve lançar

    assert stock.name is None


async def test_get_price_change_computes_pct(db_session):
    stock = Stock(ticker="NVDA")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    db_session.add(PriceSnapshot(stock_id=stock.id, date=today - timedelta(days=1), close=Decimal("100.00")))
    db_session.add(PriceSnapshot(stock_id=stock.id, date=today, close=Decimal("105.00")))
    await db_session.flush()

    last, change_pct = await market_data.get_price_change(db_session, stock.id)

    assert last == Decimal("105.00")
    assert change_pct == Decimal("5.0")


async def test_get_price_change_single_snapshot_has_no_pct(db_session):
    stock = Stock(ticker="AMZN")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    db_session.add(PriceSnapshot(stock_id=stock.id, date=today, close=Decimal("50.00")))
    await db_session.flush()

    last, change_pct = await market_data.get_price_change(db_session, stock.id)

    assert last == Decimal("50.00")
    assert change_pct is None


async def test_get_price_change_no_snapshots(db_session):
    stock = Stock(ticker="META")
    db_session.add(stock)
    await db_session.flush()

    last, change_pct = await market_data.get_price_change(db_session, stock.id)

    assert last is None
    assert change_pct is None


async def test_refresh_fundamentals_maps_extended_metrics(db_session):
    stock = Stock(ticker="AAPL", currency="USD")
    db_session.add(stock)
    await db_session.flush()

    metric_payload = {
        "metric": {
            "peTTM": 28.5,
            "epsTTM": 6.1,
            "totalDebt/totalEquityAnnual": 1.8,
            "currentDividendYieldTTM": 0.5,  # -> 0.005 guardado
            "marketCapitalization": 3_000_000,  # milhões -> *1e6
            "revenueGrowthTTMYoy": 8.2,
            "netProfitMarginTTM": 25.3,
            "roeTTM": 147.9,
            "currentRatioAnnual": 1.05,
        }
    }
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=metric_payload)):
        await market_data.refresh_fundamentals(db_session, stock)

    from app.models import FundamentalsSnapshot
    from sqlalchemy import select
    row = (
        await db_session.execute(select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock.id))
    ).scalar_one()
    assert row.pe_ratio == Decimal("28.5")
    assert row.revenue_growth == Decimal("8.2")
    assert row.net_margin == Decimal("25.3")
    assert row.roe == Decimal("147.9")
    assert row.current_ratio == Decimal("1.05")


async def test_get_market_pulse_happy_path():
    quote = {"c": 500.0, "dp": 1.23}
    news = [{"headline": "Mercado sobe", "source": "Reuters", "url": "http://x"}, {"headline": None}]

    async def fake_finnhub_get(path, params):
        if path == "quote":
            return quote
        if path == "news":
            return news
        raise AssertionError(f"unexpected path {path}")

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=fake_finnhub_get)):
        pulse = await market_data.get_market_pulse()

    assert len(pulse["indices"]) == len(market_data.MARKET_INDEX_PROXIES)
    assert all(idx["change_pct"] == 1.23 for idx in pulse["indices"])
    # a notícia sem headline é descartada
    assert pulse["news"] == [{"headline": "Mercado sobe", "source": "Reuters", "url": "http://x"}]


async def test_get_market_pulse_survives_finnhub_failure():
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=Exception("boom"))):
        pulse = await market_data.get_market_pulse()  # não deve lançar

    assert len(pulse["indices"]) == len(market_data.MARKET_INDEX_PROXIES)
    assert all(idx["change_pct"] is None for idx in pulse["indices"])
    assert pulse["news"] == []
