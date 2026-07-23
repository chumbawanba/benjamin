from app.services import backtest_core


def _cyclical_closes(cycles: int = 3, amplitude: float = 20.0, base: float = 100.0) -> list[float]:
    """Serie com quedas e subidas marcadas, para gerar RSI sobrevendido/
    sobrecomprado em pontos previsiveis (dip a meio de cada ciclo, pico no
    fim)."""
    closes = []
    for _ in range(cycles):
        for i in range(15):
            closes.append(base - amplitude * (i / 14))  # desce
        for i in range(15):
            closes.append(base - amplitude + amplitude * (i / 14))  # sobe
    return closes


def test_simulate_executes_buy_and_sell_trades():
    closes = _cyclical_closes()
    fundamentals = {"PE_RATIO": None, "DIVIDEND_YIELD": None, "EPS": None,
                     "DEBT_TO_EQUITY": None, "MARKET_CAP": None}
    series = backtest_core.build_stock_series("TEST", closes, fundamentals)
    items = [
        {"metric": "RSI_14", "operator": "<", "threshold_value": 30,
         "threshold_value_max": None, "weight": 1, "direction": "buy_signal"},
        {"metric": "RSI_14", "operator": ">", "threshold_value": 70,
         "threshold_value_max": None, "weight": 1, "direction": "sell_signal"},
    ]
    result = backtest_core.simulate(series, items, warmup_days=20)
    assert result["trades"] >= 2
    assert isinstance(result["return_pct"], float)


def test_simulate_record_trades_returns_dated_events():
    closes = _cyclical_closes()
    today_offsets = list(range(len(closes)))  # datas fictícias, só para testar o alinhamento
    dates = [f"day-{i}" for i in today_offsets]
    fundamentals = {"PE_RATIO": None, "DIVIDEND_YIELD": None, "EPS": None,
                     "DEBT_TO_EQUITY": None, "MARKET_CAP": None}
    series = backtest_core.build_stock_series("TEST", closes, fundamentals, dates=dates)
    items = [
        {"metric": "RSI_14", "operator": "<", "threshold_value": 30,
         "threshold_value_max": None, "weight": 1, "direction": "buy_signal"},
        {"metric": "RSI_14", "operator": ">", "threshold_value": 70,
         "threshold_value_max": None, "weight": 1, "direction": "sell_signal"},
    ]
    result = backtest_core.simulate(series, items, warmup_days=20, record_trades=True)
    assert "trade_events" in result
    assert len(result["trade_events"]) == result["trades"]
    assert result["trade_events"][0]["action"] == "BUY"
    for event in result["trade_events"]:
        assert event["date"] in dates
        assert event["price"] in closes


def test_simulate_without_record_trades_omits_trade_events():
    closes = _cyclical_closes()
    series = backtest_core.build_stock_series("TEST", closes, {})
    result = backtest_core.simulate(series, [], warmup_days=20)
    assert "trade_events" not in result


def test_simulate_never_trades_with_empty_ruleset():
    closes = _cyclical_closes()
    series = backtest_core.build_stock_series("TEST", closes, {})
    result = backtest_core.simulate(series, [], warmup_days=20)
    assert result["trades"] == 0
    assert result["return_pct"] == 0.0


def test_buy_and_hold_return_positive_for_uptrend():
    closes = [100.0 + i for i in range(60)]
    series = backtest_core.build_stock_series("TEST", closes, {})
    ret = backtest_core.buy_and_hold_return(series, warmup_days=30)
    assert ret is not None and ret > 0


def test_buy_and_hold_return_none_when_not_enough_history():
    series = backtest_core.build_stock_series("TEST", [100.0], {})
    assert backtest_core.buy_and_hold_return(series, warmup_days=30) is None


def test_optimize_never_worse_than_empty_baseline():
    closes = _cyclical_closes()
    fundamentals = {"PE_RATIO": 12.0, "DIVIDEND_YIELD": 0.02, "EPS": 3.0,
                     "DEBT_TO_EQUITY": 0.5, "MARKET_CAP": 50.0}
    series = backtest_core.build_stock_series("TEST", closes, fundamentals)
    result = backtest_core.optimize([series])
    assert result["stocks_evaluated"] == 1
    assert len(result["items"]) <= backtest_core.MAX_ITEMS
    assert result["backtest_return_pct"] >= 0.0


def test_optimize_with_no_series_returns_empty():
    result = backtest_core.optimize([])
    assert result["items"] == []
    assert result["backtest_return_pct"] == 0.0
    assert result["buy_and_hold_return_pct"] is None
    assert result["stocks_evaluated"] == 0


def test_fundamentals_to_observed_applies_scale():
    class FakeRow:
        pe_ratio = 15.0
        eps = 2.0
        debt_to_equity = 0.8
        dividend_yield = 0.01
        market_cap = 5_000_000_000
        roe = 18.5
        net_margin = 22.0
        revenue_growth = 8.5

    observed = backtest_core.fundamentals_to_observed(FakeRow())
    assert observed["PE_RATIO"] == 15.0
    assert observed["MARKET_CAP"] == 5.0  # escalado para mil milhoes
    assert observed["ROE"] == 18.5  # sem escala - ja vem em percentagem
    assert observed["NET_MARGIN"] == 22.0
    assert observed["REVENUE_GROWTH"] == 8.5


def test_fundamentals_to_observed_handles_none_row():
    observed = backtest_core.fundamentals_to_observed(None)
    assert all(v is None for v in observed.values())
    assert set(observed.keys()) == {
        "PE_RATIO", "DIVIDEND_YIELD", "EPS", "DEBT_TO_EQUITY", "MARKET_CAP",
        "ROE", "NET_MARGIN", "REVENUE_GROWTH",
        "GROSS_MARGIN", "OPERATING_MARGIN", "EPS_GROWTH", "DIVIDEND_GROWTH_5Y",
    }
