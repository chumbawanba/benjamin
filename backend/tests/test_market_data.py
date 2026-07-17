"""Testes unitários para o backfill de perfil (nome/exchange/sector/currency)
em falta — cobre o caso em que a Finnhub estava indisponível/rate-limited no
momento em que a stock foi criada (ver validate_and_create_stock)."""
from unittest.mock import AsyncMock, patch

from app.models import Stock
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
