"""Testes de app/services/synthesis.py — a síntese visual por categoria
(valuation/momentum/crescimento/rendibilidade) usada na StockDetail."""
from app.services.synthesis import compute_synthesis


def test_all_favoravel_gives_score_100():
    values = {
        "PE_RATIO": 10.0,  # < 15 -> favorável
        "RSI_14": 25.0,  # <= 30 -> favorável
        "ROE": 20.0,  # >= 15 -> favorável
    }
    result = compute_synthesis(values)
    assert result.score == 100.0

    valuation = next(c for c in result.categories if c.category == "valuation")
    assert valuation.classification == "favoravel"
    assert "PE 10.0" in valuation.reason

    profitability = next(c for c in result.categories if c.category == "profitability")
    assert profitability.classification == "favoravel"


def test_all_desfavoravel_gives_score_0():
    values = {"PE_RATIO": 50.0, "RSI_14": 80.0, "ROE": 2.0}
    result = compute_synthesis(values)
    assert result.score == 0.0
    for cat in ("valuation", "profitability"):
        entry = next(c for c in result.categories if c.category == cat)
        assert entry.classification == "desfavoravel"


def test_mixed_signals_in_same_category_gives_misto():
    """RSI sobrecomprado (desfavorável) mas preço acima da SMA_50
    (favorável) - a categoria momentum não deve fingir consenso."""
    values = {"RSI_14": 80.0, "PRICE_VS_SMA_50": 10.0}
    result = compute_synthesis(values)
    momentum = next(c for c in result.categories if c.category == "momentum")
    assert momentum.classification == "misto"
    assert "RSI 80" in momentum.reason
    assert "vs SMA 50" in momentum.reason


def test_category_without_data_is_none_not_zero():
    """Sem nenhum indicador de crescimento disponível, a categoria deve
    aparecer como "sem dados" (None), não ser tratada como desfavorável."""
    result = compute_synthesis({"PE_RATIO": 10.0})
    growth = next(c for c in result.categories if c.category == "growth")
    assert growth.classification is None
    assert growth.reason is None


def test_no_indicators_at_all_gives_none_score():
    result = compute_synthesis({})
    assert result.score is None
    assert all(c.classification is None for c in result.categories)


def test_ignores_indicators_outside_the_scoring_rules():
    """DIVIDEND_YIELD/DEBT_TO_EQUITY/MARKET_CAP não entram no score (ver
    docstring de synthesis.py) - só continuam na grelha de indicadores."""
    values = {"DIVIDEND_YIELD": 0.05, "DEBT_TO_EQUITY": 3.0, "MARKET_CAP": 500.0}
    result = compute_synthesis(values)
    assert result.score is None


def test_neutral_value_counts_as_half_weight_in_score():
    """PE_RATIO=20 está na zona neutra (nem <15 nem >=30) - conta meio
    peso no score em vez de peso cheio como favorável/desfavorável."""
    result = compute_synthesis({"PE_RATIO": 20.0})
    assert result.score == 50.0
    valuation = next(c for c in result.categories if c.category == "valuation")
    assert valuation.classification == "neutro"
