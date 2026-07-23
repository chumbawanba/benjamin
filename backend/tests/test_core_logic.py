"""Testes do nucleo puro (indicadores + agente).

Corriveis com unittest (stdlib) neste ambiente; tambem compativeis com pytest.
"""
import unittest

import pandas as pd

from app.services.agent_core import apply_operator, compute_evaluation
from app.services.indicators_core import INDICATORS, calc_price_vs_sma, calc_rsi, calc_sma, latest_close


def make_items():
    """Estrategia 'Value simples' - exemplo de referencia do SPEC seccao 6."""
    return [
        {"id": 1, "metric": "RSI_14", "operator": "<", "threshold_value": 30,
         "weight": 2, "direction": "buy_signal"},
        {"id": 2, "metric": "PE_RATIO", "operator": "<", "threshold_value": 15,
         "weight": 1, "direction": "buy_signal"},
        {"id": 3, "metric": "RSI_14", "operator": ">", "threshold_value": 70,
         "weight": 1, "direction": "sell_signal"},
    ]


class TestAgentReferenceExamples(unittest.TestCase):
    def test_spec_example_buy(self):
        """RSI=25, PE=12 -> buy_score=100, sell_score=0, BUY."""
        result = compute_evaluation(make_items(), {"RSI_14": 25, "PE_RATIO": 12})
        self.assertEqual(result.buy_score, 100.0)
        self.assertEqual(result.sell_score, 0.0)
        self.assertEqual(result.recommendation, "BUY")
        self.assertEqual(len(result.details), 3)

    def test_spec_example_missing_fundamental(self):
        """RSI=50, PE=None -> buy_score=0, HOLD, detail do PE com passed=None."""
        result = compute_evaluation(make_items(), {"RSI_14": 50, "PE_RATIO": None})
        self.assertEqual(result.buy_score, 0.0)
        self.assertEqual(result.sell_score, 0.0)
        self.assertEqual(result.recommendation, "HOLD")
        pe_detail = [d for d in result.details if d.item_id == 2][0]
        self.assertIsNone(pe_detail.passed)
        self.assertEqual(pe_detail.contribution, 0.0)

    def test_sell_takes_priority(self):
        """RSI=80 -> sinal de venda dispara e tem prioridade."""
        result = compute_evaluation(make_items(), {"RSI_14": 80, "PE_RATIO": 10})
        self.assertEqual(result.sell_score, 100.0)
        self.assertEqual(result.recommendation, "SELL")

    def test_partial_buy_score(self):
        """So o criterio PE passa (peso 1 de 3) -> buy_score = 33.33."""
        result = compute_evaluation(make_items(), {"RSI_14": 50, "PE_RATIO": 10})
        self.assertAlmostEqual(result.buy_score, 33.33, places=2)
        self.assertEqual(result.recommendation, "HOLD")

    def test_no_evaluable_criteria(self):
        result = compute_evaluation(make_items(), {"RSI_14": None, "PE_RATIO": None})
        self.assertEqual(result.buy_score, 0.0)
        self.assertEqual(result.sell_score, 0.0)
        self.assertEqual(result.recommendation, "HOLD")


class TestOperators(unittest.TestCase):
    def test_all_operators(self):
        self.assertTrue(apply_operator(5, "<", 10))
        self.assertFalse(apply_operator(10, "<", 5))
        self.assertTrue(apply_operator(10, ">", 5))
        self.assertTrue(apply_operator(5, "<=", 5))
        self.assertTrue(apply_operator(5, ">=", 5))
        self.assertTrue(apply_operator(5, "==", 5))
        self.assertTrue(apply_operator(7, "between", 5, 10))
        self.assertFalse(apply_operator(11, "between", 5, 10))

    def test_unknown_operator_raises(self):
        with self.assertRaises(ValueError):
            apply_operator(1, "!=", 1)

    def test_between_requires_max(self):
        with self.assertRaises(ValueError):
            apply_operator(1, "between", 5, None)


class TestIndicators(unittest.TestCase):
    def test_sma_known_value(self):
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(calc_sma(closes, 5), 3.0)
        self.assertEqual(calc_sma(closes, 3), 4.0)  # media dos ultimos 3

    def test_sma_insufficient_history(self):
        self.assertIsNone(calc_sma(pd.Series([1.0, 2.0]), 5))

    def test_rsi_all_gains_is_100(self):
        closes = pd.Series(range(1, 31), dtype=float)  # 30 dias sempre a subir
        self.assertEqual(calc_rsi(closes, 14), 100.0)

    def test_rsi_all_losses_near_0(self):
        closes = pd.Series(range(60, 30, -1), dtype=float)  # sempre a descer
        rsi = calc_rsi(closes, 14)
        self.assertIsNotNone(rsi)
        self.assertLess(rsi, 1.0)

    def test_rsi_flat_then_mixed_in_range(self):
        closes = pd.Series([50, 51, 50, 52, 51, 53, 52, 54, 53, 55,
                            54, 56, 55, 57, 56, 58, 57, 59, 58, 60], dtype=float)
        rsi = calc_rsi(closes, 14)
        self.assertIsNotNone(rsi)
        self.assertGreater(rsi, 50.0)  # tendencia de subida -> RSI > 50
        self.assertLess(rsi, 100.0)

    def test_rsi_insufficient_history(self):
        self.assertIsNone(calc_rsi(pd.Series([1.0] * 10), 14))

    def test_latest_close(self):
        self.assertEqual(latest_close(pd.Series([1.0, 2.0, 9.5])), 9.5)
        self.assertIsNone(latest_close(pd.Series([], dtype=float)))

    def test_registry_has_all_mvp_indicators(self):
        expected = {
            "PRICE_CLOSE", "RSI_14", "SMA_50", "SMA_200", "PE_RATIO", "DIVIDEND_YIELD",
            "EPS", "DEBT_TO_EQUITY", "MARKET_CAP", "PRICE_VS_SMA_50", "PRICE_VS_SMA_200",
            "ROE", "NET_MARGIN", "REVENUE_GROWTH",
            "GROSS_MARGIN", "OPERATING_MARGIN", "EPS_GROWTH", "DIVIDEND_GROWTH_5Y",
        }
        self.assertEqual(set(INDICATORS.keys()), expected)

    def test_price_vs_sma_known_value(self):
        # SMA(5) dos ultimos 5 valores = 3.0; ultimo fecho = 5.0 -> (5-3)/3*100
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertAlmostEqual(calc_price_vs_sma(closes, 5), 66.6666, places=3)

    def test_price_vs_sma_price_below_average_is_negative(self):
        closes = pd.Series([10.0, 9.0, 8.0, 7.0, 6.0])  # SMA=8, ultimo=6 -> -25%
        self.assertAlmostEqual(calc_price_vs_sma(closes, 5), -25.0, places=3)

    def test_price_vs_sma_insufficient_history(self):
        self.assertIsNone(calc_price_vs_sma(pd.Series([1.0, 2.0]), 5))

    def test_price_vs_sma_scale_invariant_across_stocks(self):
        """A mesma forma relativa (10% acima da media) da o mesmo resultado
        independentemente do nivel de preco - e exatamente o que SMA_200
        sozinho nao garante (ver conversa com o utilizador sobre acoes com
        precos muito diferentes na mesma estrategia)."""
        cheap_stock = pd.Series([18.0, 19.0, 20.0, 21.0, 22.0])  # SMA=20, ultimo=22
        expensive_stock = pd.Series([1800.0, 1900.0, 2000.0, 2100.0, 2200.0])  # SMA=2000, ultimo=2200
        self.assertAlmostEqual(
            calc_price_vs_sma(cheap_stock, 5), calc_price_vs_sma(expensive_stock, 5), places=6
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
