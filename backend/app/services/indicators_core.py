"""Calculo puro de indicadores tecnicos. Sem dependencias de BD - testavel isoladamente.

Todas as funcoes recebem uma pandas Series de precos de fecho (ordem cronologica
ascendente) e devolvem float ou None se nao houver historico suficiente.
"""
import pandas as pd


def calc_sma(closes: pd.Series, period: int) -> float | None:
    if closes is None or len(closes) < period:
        return None
    return float(closes.tail(period).mean())


def calc_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """RSI pelo metodo de Wilder (smoothing exponencial alpha=1/period)."""
    if closes is None or len(closes) < period + 1:
        return None
    delta = closes.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if pd.isna(last_gain) or pd.isna(last_loss):
        return None
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return float(100.0 - 100.0 / (1.0 + rs))


def latest_close(closes: pd.Series) -> float | None:
    if closes is None or len(closes) == 0:
        return None
    return float(closes.iloc[-1])


# Registry: chave -> (funcao(closes|fundamental), lookback_days, tipo)
# tipo "price": recebe Series de closes; tipo "fundamental": lookup direto por campo.
INDICATORS: dict[str, dict] = {
    "PRICE_CLOSE": {"kind": "price", "fn": latest_close, "lookback_days": 1},
    "RSI_14": {"kind": "price", "fn": lambda c: calc_rsi(c, 14), "lookback_days": 30},
    "SMA_50": {"kind": "price", "fn": lambda c: calc_sma(c, 50), "lookback_days": 60},
    "SMA_200": {"kind": "price", "fn": lambda c: calc_sma(c, 200), "lookback_days": 210},
    "PE_RATIO": {"kind": "fundamental", "field": "pe_ratio", "lookback_days": 0},
    "DIVIDEND_YIELD": {"kind": "fundamental", "field": "dividend_yield", "lookback_days": 0},
}
