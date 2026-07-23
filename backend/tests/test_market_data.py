"""Testes unitários para o backfill de perfil (nome/exchange/sector/currency)
em falta — cobre o caso em que a Finnhub estava indisponível/rate-limited no
momento em que a stock foi criada (ver validate_and_create_stock)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

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


def test_market_hint_from_ticker_known_suffix():
    assert market_data._market_hint_from_ticker("VWCE.LS") == "Lisboa"


def test_market_hint_from_ticker_unknown_suffix_falls_back_to_raw():
    assert market_data._market_hint_from_ticker("XYZ.ZZ") == "ZZ"


def test_market_hint_from_ticker_no_suffix_is_eua():
    assert market_data._market_hint_from_ticker("AAPL") == "EUA"


async def test_search_tickers_prioritizes_listings_without_exchange_suffix(db_session):
    """Um ETF UCITS cross-listado (ex: VWCE) devolve várias entradas com
    sufixo de bolsa (.DE, .MI, ...) e nenhuma óbvia - a listagem sem sufixo
    (tipicamente EUA, mais provável de ter histórico nos fornecedores usados)
    deve vir primeiro, para não obrigar o utilizador a decifrar qual escolher."""
    fake_response = {
        "result": [
            {"symbol": "VWCE.MI", "description": "VANGUARD FTSE ALL-WORLD...,MI", "type": "ETP"},
            {"symbol": "VWCE.DE", "description": "VANGUARD FTSE ALL-WORLD...,DE", "type": "ETP"},
            {"symbol": "VWCE", "description": "VANGUARD FTSE ALL-WORLD ETF", "type": "ETP"},
        ],
    }
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_response)):
        results = await market_data.search_tickers("vwce")

    assert results[0]["ticker"] == "VWCE"
    assert results[0]["market_hint"] == "EUA"


async def test_search_tickers_includes_type_and_market_hint(db_session):
    fake_response = {
        "result": [{"symbol": "AAPL", "description": "Apple Inc.", "type": "Common Stock"}],
    }
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_response)):
        results = await market_data.search_tickers("apple")

    assert results == [{
        "ticker": "AAPL", "name": "Apple Inc.", "type": "Common Stock", "market_hint": "EUA",
    }]


async def test_search_tickers_respects_limit_after_sorting(db_session):
    fake_response = {
        "result": [{"symbol": f"T{i}.DE", "description": f"Ticker {i}", "type": "ETP"} for i in range(10)],
    }
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_response)):
        results = await market_data.search_tickers("t", limit=3)

    assert len(results) == 3


async def test_validate_and_create_stock_accepts_etf_when_stock_profile_empty(db_session):
    """SPY não é reconhecido por /stock/profile2 (endpoint de empresa), mas
    /etf/profile devolve dados - deve aceitar-se como ETF em vez de rejeitar."""
    async def fake_finnhub_get(path, params):
        if path == "stock/profile2":
            return {}
        if path == "etf/profile":
            return {"profile": {"name": "SPDR S&P 500 ETF Trust", "currency": "USD"}}
        raise AssertionError(f"unexpected path {path}")

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=fake_finnhub_get)):
        stock = await market_data.validate_and_create_stock(db_session, "SPY")

    assert stock is not None
    assert stock.asset_type == "etf"
    assert stock.name == "SPDR S&P 500 ETF Trust"
    assert stock.currency == "USD"


async def test_validate_and_create_stock_rejects_when_neither_stock_nor_etf(db_session):
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value={})):
        stock = await market_data.validate_and_create_stock(db_session, "NAOEXISTE")

    assert stock is None


async def test_validate_and_create_stock_defaults_to_stock_type(db_session):
    """Regressão: quando /stock/profile2 já tem dados, nem tenta o ETF - fica
    com asset_type='stock' (comportamento anterior a esta coluna existir)."""
    profile = {"name": "Apple Inc.", "currency": "USD", "exchange": "NASDAQ", "finnhubIndustry": "Technology"}
    mock = AsyncMock(return_value=profile)
    with patch("app.services.market_data._finnhub_get", new=mock):
        stock = await market_data.validate_and_create_stock(db_session, "AAPL")

    assert stock.asset_type == "stock"
    mock.assert_called_once()  # só stock/profile2 - nunca chegou a tentar etf/profile


async def test_backfill_profile_falls_back_to_etf(db_session):
    stock = Stock(ticker="VWCE")  # simula stock criada sem metadados
    db_session.add(stock)
    await db_session.flush()

    async def fake_finnhub_get(path, params):
        if path == "stock/profile2":
            return {}
        if path == "etf/profile":
            return {"profile": {"name": "Vanguard FTSE All-World", "currency": "EUR"}}
        raise AssertionError(f"unexpected path {path}")

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=fake_finnhub_get)):
        await market_data._backfill_profile(db_session, stock)

    assert stock.name == "Vanguard FTSE All-World"
    assert stock.asset_type == "etf"


async def test_refresh_fundamentals_skips_stock_metric_for_etf(db_session):
    stock = Stock(ticker="SPY", currency="USD", asset_type="etf")
    db_session.add(stock)
    await db_session.flush()

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=AssertionError("não devia ser chamado"))):
        await market_data.refresh_fundamentals(db_session, stock)  # não deve lançar/chamar a Finnhub

    from sqlalchemy import select

    from app.models import FundamentalsSnapshot
    rows = (await db_session.execute(select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock.id))).scalars().all()
    assert rows == []


async def test_refresh_fundamentals_skips_retry_within_cooldown(db_session):
    """Um símbolo que a Finnhub rejeita sempre em /stock/metric (ex: sem
    cobertura de fundamentais) nunca cria um FundamentalsSnapshot, logo nunca
    satisfaz o `existing` - sem FUNDAMENTALS_RETRY_COOLDOWN, tentava-se de
    novo em toda a chamada."""
    from app.models import FundamentalsSnapshot

    stock = Stock(
        ticker="AAPL", currency="USD",
        last_fundamentals_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(stock)
    await db_session.flush()

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=AssertionError("não devia ser chamado"))):
        await market_data.refresh_fundamentals(db_session, stock)  # não deve lançar/chamar a Finnhub

    rows = (await db_session.execute(select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock.id))).scalars().all()
    assert rows == []


async def test_refresh_fundamentals_retries_after_cooldown_expires(db_session):
    """Passado o FUNDAMENTALS_RETRY_COOLDOWN, volta a tentar-se - o cooldown
    protege a Finnhub mas não bloqueia para sempre."""
    stock = Stock(
        ticker="MSFT", currency="USD",
        last_fundamentals_attempt_at=datetime.now(timezone.utc) - market_data.FUNDAMENTALS_RETRY_COOLDOWN - timedelta(minutes=1),
    )
    db_session.add(stock)
    await db_session.flush()

    finnhub_mock = AsyncMock(return_value={"metric": {"roeTTM": 33.13, "netProfitMarginTTM": 39.34, "revenueGrowthTTMYoy": 17.87}})
    with patch("app.services.market_data._finnhub_get", new=finnhub_mock):
        await market_data.refresh_fundamentals(db_session, stock)

    finnhub_mock.assert_called_once_with("stock/metric", {"symbol": "MSFT", "metric": "all"})
    assert stock.last_fundamentals_attempt_at is not None


async def test_ensure_fresh_still_refreshes_fundamentals_when_history_sufficient(db_session):
    """Bug real: MSFT numa watchlist há semanas (histórico já suficiente)
    nunca mais tinha ROE/margem/crescimento atualizados - refresh_fundamentals
    só corria dentro do ramo de backfill do ensure_fresh, nunca percorrido de
    novo por uma ação já 'fresca'. Confirma que, mesmo com histórico
    suficiente, o snapshot de fundamentais de HOJE é criado com os campos
    confirmados no payload real da Finnhub (ver comentário no topo do
    ficheiro)."""
    stock = Stock(ticker="MSFT", name="Microsoft Corp", currency="USD")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    for i in range(market_data.MIN_HISTORY_ROWS):
        db_session.add(PriceSnapshot(
            stock_id=stock.id, date=today - timedelta(days=i), close=Decimal("397.75"),
        ))
    await db_session.commit()

    metric_payload = {
        "metric": {
            "peTTM": 23.71, "epsTTM": 16.79, "totalDebt/totalEquityAnnual": 0.26,
            "currentDividendYieldTTM": 0.87, "marketCapitalization": 2968700,
            "roeTTM": 33.13, "netProfitMarginTTM": 39.34, "revenueGrowthTTMYoy": 17.87,
        }
    }
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=[{"c": 397.75}, metric_payload])):
        await market_data.ensure_fresh(db_session, stock)

    from app.models import FundamentalsSnapshot
    row = (
        await db_session.execute(
            select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock.id, FundamentalsSnapshot.date == today)
        )
    ).scalar_one()
    assert row.roe == Decimal("33.13")
    assert row.net_margin == Decimal("39.34")
    assert row.revenue_growth == Decimal("17.87")


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


async def test_ensure_fresh_retries_when_recent_but_insufficient_history(db_session):
    """Uma stock com um snapshot de HOJE (ex: só o /quote da Finnhub alguma
    vez funcionou) mas muito abaixo de MIN_HISTORY_ROWS não pode ficar
    'fresca' para sempre - sem isto, o backfill de histórico nunca mais era
    tentado outra vez (ver bug real: BRK.B preso em histórico insuficiente)."""
    stock = Stock(ticker="AAPL", name="Apple Inc.", currency="USD")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    db_session.add(PriceSnapshot(stock_id=stock.id, date=today, close=Decimal("150.00")))
    await db_session.commit()

    finnhub_mock = AsyncMock(return_value={"c": 151.0})
    twelvedata_mock = AsyncMock(return_value={"values": []})
    with patch("app.services.market_data._finnhub_get", new=finnhub_mock), \
         patch("app.services.market_data._twelvedata_get", new=twelvedata_mock):
        await market_data.ensure_fresh(db_session, stock)

    # refresh_prices chamou a Twelve Data outra vez apesar do snapshot de hoje já existir
    twelvedata_mock.assert_called()


async def test_ensure_fresh_skips_when_recent_and_sufficient_history(db_session):
    """Com histórico completo (>= MIN_HISTORY_ROWS) e um snapshot recente, o
    curto-circuito de freshness do BACKFILL continua a funcionar - não deve
    voltar a chamar a Twelve Data. Mas a cotação E os fundamentais de hoje
    ainda são atualizados via Finnhub (ver
    test_ensure_fresh_still_refreshes_quote_when_history_sufficient e
    test_ensure_fresh_still_refreshes_fundamentals_when_history_sufficient -
    este é o comportamento novo que resolve preço/fundamentais ficarem
    congelados)."""
    stock = Stock(ticker="AAPL", name="Apple Inc.", currency="USD")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    for i in range(market_data.MIN_HISTORY_ROWS):
        db_session.add(PriceSnapshot(
            stock_id=stock.id, date=today - timedelta(days=i), close=Decimal("150.00"),
        ))
    await db_session.commit()

    finnhub_mock = AsyncMock(return_value={"c": 152.0})
    with patch("app.services.market_data._finnhub_get", new=finnhub_mock), \
         patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=AssertionError("não devia ser chamado"))):
        await market_data.ensure_fresh(db_session, stock)  # não deve lançar

    finnhub_mock.assert_any_call("quote", {"symbol": "AAPL"})
    finnhub_mock.assert_any_call("stock/metric", {"symbol": "AAPL", "metric": "all"})
    assert finnhub_mock.call_count == 2


async def test_ensure_fresh_still_refreshes_quote_when_history_sufficient(db_session):
    """Bug real: GOOG caiu ~6% intradiário e a app continuava a mostrar o
    preço da 1ª consulta do dia - ensure_fresh nunca voltava a chamar a
    Finnhub depois de ter histórico e snapshot de hoje. Com histórico
    suficiente, o snapshot de HOJE deve ser atualizado (upsert), não só criado
    uma vez."""
    stock = Stock(ticker="GOOG", name="Alphabet Inc.", currency="USD")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    for i in range(market_data.MIN_HISTORY_ROWS):
        db_session.add(PriceSnapshot(
            stock_id=stock.id, date=today - timedelta(days=i), close=Decimal("200.00"),
        ))
    await db_session.commit()

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value={"c": 188.0, "h": 201.0, "l": 187.5})):
        await market_data.ensure_fresh(db_session, stock)

    row = (
        await db_session.execute(
            select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id, PriceSnapshot.date == today)
        )
    ).scalar_one()
    assert row.close == Decimal("188")
    assert stock.last_quote_at is not None


async def test_ensure_fresh_skips_quote_refresh_within_cooldown(db_session):
    """Duas visitas seguidas à mesma ação dentro de QUOTE_REFRESH_COOLDOWN não
    devem martelar a Finnhub - só passado o cooldown é que se tenta de novo.
    last_fundamentals_attempt_at também recente, para isolar este teste ao
    comportamento do cooldown de cotação especificamente (ver
    test_refresh_fundamentals_skips_retry_within_cooldown para o equivalente
    dos fundamentais)."""
    stock = Stock(
        ticker="AAPL", name="Apple Inc.", currency="USD",
        last_quote_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        last_fundamentals_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    for i in range(market_data.MIN_HISTORY_ROWS):
        db_session.add(PriceSnapshot(
            stock_id=stock.id, date=today - timedelta(days=i), close=Decimal("150.00"),
        ))
    await db_session.commit()

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=AssertionError("não devia ser chamado"))):
        await market_data.ensure_fresh(db_session, stock)  # não deve lançar


async def test_ensure_fresh_skips_retry_when_recently_attempted_and_still_insufficient(db_session):
    """Um ticker rejeitado permanentemente pelos fornecedores (ex: VUSA.F, fora
    de cobertura do plano gratuito) nunca acumula histórico suficiente - sem o
    cooldown, o cascade completo de retries corria em TODA a visita à página,
    esgotando a quota partilhada da Twelve Data. Com uma tentativa recente
    (dentro de BACKFILL_RETRY_COOLDOWN), não deve chamar nenhum fornecedor."""
    stock = Stock(
        ticker="VUSA.F", currency="EUR",
        last_backfill_attempt_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(stock)
    await db_session.flush()

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(side_effect=AssertionError("não devia ser chamado"))), \
         patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=AssertionError("não devia ser chamado"))):
        await market_data.ensure_fresh(db_session, stock)  # não deve lançar


async def test_ensure_fresh_retries_after_cooldown_expires(db_session):
    """Passado o BACKFILL_RETRY_COOLDOWN, o retry volta a ser tentado - o
    cooldown protege a quota partilhada mas não bloqueia para sempre."""
    stock = Stock(
        ticker="VUSA.F", currency="EUR",
        last_backfill_attempt_at=datetime.now(timezone.utc) - market_data.BACKFILL_RETRY_COOLDOWN - timedelta(minutes=1),
    )
    db_session.add(stock)
    await db_session.flush()

    finnhub_mock = AsyncMock(return_value={"c": 0})
    twelvedata_mock = AsyncMock(return_value={"values": []})
    with patch("app.services.market_data._finnhub_get", new=finnhub_mock), \
         patch("app.services.market_data._twelvedata_get", new=twelvedata_mock):
        await market_data.ensure_fresh(db_session, stock)

    twelvedata_mock.assert_called()


async def test_ensure_fresh_sets_last_backfill_attempt_at_after_retry(db_session):
    """Depois de uma tentativa (mesmo sem histórico suficiente ainda),
    last_backfill_attempt_at deve ficar atualizado para ativar o cooldown na
    próxima chamada."""
    stock = Stock(ticker="VUSA.F", currency="EUR")
    db_session.add(stock)
    await db_session.flush()
    assert stock.last_backfill_attempt_at is None

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value={"c": 0})), \
         patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"values": []})):
        await market_data.ensure_fresh(db_session, stock)

    assert stock.last_backfill_attempt_at is not None


def test_alt_ticker_symbol_swaps_dot_to_hyphen():
    assert market_data._alt_ticker_symbol("BRK.B") == "BRK-B"


def test_alt_ticker_symbol_swaps_hyphen_to_dot():
    assert market_data._alt_ticker_symbol("BRK-B") == "BRK.B"


def test_alt_ticker_symbol_none_without_punctuation():
    assert market_data._alt_ticker_symbol("AAPL") is None


async def test_backfill_history_falls_back_to_alt_symbol_format(db_session):
    """Reproduz o caso da Berkshire classe B: a stock fica guardada como
    'BRK.B' (formato devolvido pela pesquisa da Finnhub), mas a Twelve Data
    só reconhece 'BRK-B' - sem o fallback, o histórico ficava sempre vazio
    (só 1 snapshot/dia via Finnhub /quote, nunca os 365 dias do backfill)."""
    stock = Stock(ticker="BRK.B", currency="USD")
    db_session.add(stock)
    await db_session.flush()

    async def fake_twelvedata_get(path, params):
        assert path == "time_series"
        if params["symbol"] == "BRK.B":
            return {"code": 400, "message": "symbol not found"}  # sem "values"
        if params["symbol"] == "BRK-B":
            return {"values": [
                {"datetime": "2026-07-20", "open": "440", "high": "445", "low": "438", "close": "442", "volume": "1000"},
                {"datetime": "2026-07-21", "open": "442", "high": "446", "low": "440", "close": "444", "volume": "1200"},
            ]}
        raise AssertionError(f"unexpected symbol {params['symbol']}")

    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=fake_twelvedata_get)):
        inserted = await market_data._backfill_history(db_session, stock, set())

    assert inserted == 2
    from sqlalchemy import select
    rows = (await db_session.execute(select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id))).scalars().all()
    assert len(rows) == 2


async def test_backfill_history_returns_zero_when_both_formats_fail(db_session):
    stock = Stock(ticker="BRK.B", currency="USD")
    db_session.add(stock)
    await db_session.flush()

    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"code": 400})):
        inserted = await market_data._backfill_history(db_session, stock, set())

    assert inserted == 0


def test_split_ticker_suffix_with_suffix():
    assert market_data._split_ticker_suffix("VUSA.F") == ("VUSA", "F")


def test_split_ticker_suffix_without_suffix():
    assert market_data._split_ticker_suffix("AAPL") == ("AAPL", None)


async def test_backfill_history_falls_back_to_mic_code_for_known_suffix(db_session):
    """Reproduz o caso do VUSA.F: a Finnhub devolve o ticker com o sufixo de
    bolsa colado ('VUSA.F' = Frankfurt), mas a Twelve Data não reconhece esse
    formato - espera o símbolo puro + mic_code (ISO 10383) à parte. Nem o
    símbolo tal como está nem a troca ponto/hífen (pensada para classes de
    ações tipo BRK.B, não sufixos de bolsa) resolvem isto; só o terceiro
    fallback (separar sufixo -> mic_code) deve funcionar."""
    stock = Stock(ticker="VUSA.F", currency="EUR")
    db_session.add(stock)
    await db_session.flush()

    async def fake_twelvedata_get(path, params):
        assert path == "time_series"
        if params["symbol"] == "VUSA" and params.get("mic_code") == "XFRA":
            return {"values": [
                {"datetime": "2026-07-20", "open": "90", "high": "91", "low": "89", "close": "90.5", "volume": "500"},
            ]}
        return {"code": 400, "message": "symbol not found"}  # 'VUSA.F' e 'VUSA-F'

    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=fake_twelvedata_get)):
        inserted = await market_data._backfill_history(db_session, stock, set())

    assert inserted == 1


async def test_backfill_history_skips_mic_code_fallback_for_unknown_suffix(db_session):
    """Sufixo sem mic_code conhecido (ver _TICKER_SUFFIX_MIC_CODES) - não deve
    sequer tentar uma 3ª chamada à Twelve Data, só a literal e a troca ./-."""
    stock = Stock(ticker="XPTO.ZZ", currency="USD")
    db_session.add(stock)
    await db_session.flush()

    calls = []

    async def fake_twelvedata_get(path, params):
        calls.append(params["symbol"])
        return {"code": 400}

    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=fake_twelvedata_get)):
        inserted = await market_data._backfill_history(db_session, stock, set())

    assert inserted == 0
    assert calls == ["XPTO.ZZ", "XPTO-ZZ"]  # sem 3ª tentativa


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
            "grossMarginTTM": 44.1,
            "operatingMarginTTM": 30.2,
            "epsGrowthTTMYoy": 22.7,
            "dividendGrowthRate5Y": 9.4,
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
    assert row.gross_margin == Decimal("44.1")
    assert row.operating_margin == Decimal("30.2")
    assert row.eps_growth == Decimal("22.7")
    assert row.dividend_growth_5y == Decimal("9.4")


async def test_refresh_fundamentals_falls_back_to_annual_margins_and_3y_eps_growth(db_session):
    """Quando os campos TTM não vêm no payload (ex: empresa sem trimestre
    reportado recente), cai para as variantes Annual/3Y - mesmo padrão já
    usado para pe/eps/revenue_growth/net_margin/roe."""
    stock = Stock(ticker="AAPL", currency="USD")
    db_session.add(stock)
    await db_session.flush()

    metric_payload = {"metric": {"grossMarginAnnual": 41.0, "operatingMarginAnnual": 28.0, "epsGrowth3Y": 12.4}}
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=metric_payload)):
        await market_data.refresh_fundamentals(db_session, stock)

    from app.models import FundamentalsSnapshot
    from sqlalchemy import select
    row = (
        await db_session.execute(select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock.id))
    ).scalar_one()
    assert row.gross_margin == Decimal("41.0")
    assert row.operating_margin == Decimal("28.0")
    assert row.eps_growth == Decimal("12.4")
    assert row.dividend_growth_5y is None


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
