from app.services.email_service import build_summary_html


def test_build_summary_html():
    rows = [
        {"ticker": "AAPL", "buy_score": 33.33, "sell_score": 100.0,
         "recommendation": "SELL", "price": 180.5, "strategy_name": "Value simples"},
        {"ticker": "MSFT", "buy_score": 100.0, "sell_score": 0.0,
         "recommendation": "BUY", "price": 420.0, "strategy_name": "Value simples"},
    ]
    html = build_summary_html(rows)
    assert "AAPL" in html and "MSFT" in html
    assert "SELL" in html and "BUY" in html
    assert html.index("MSFT") < html.index("AAPL")  # ordenado por buy_score desc


def test_send_summary_without_smtp_config(caplog):
    from app.services.email_service import send_summary
    assert send_summary([{"ticker": "X", "buy_score": 0, "sell_score": 0,
                          "recommendation": "HOLD", "price": None,
                          "strategy_name": "T"}]) is False


def test_send_summary_empty_rows():
    from app.services.email_service import send_summary
    assert send_summary([]) is False
