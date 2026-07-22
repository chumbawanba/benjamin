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


# Registry: chave -> (funcao(closes|fundamental), lookback_days, tipo, descricao)
# tipo "price": recebe Series de closes; tipo "fundamental": lookup direto por campo.
# "description": explicação curta do que é a métrica.
# "unit": formato/escala em que o threshold deve ser escrito no editor de
# estratégias (ex: fração vs percentagem, rácio, moeda) - o erro mais comum
# sem isto é confundir DIVIDEND_YIELD (fração, 0.02) com uma percentagem (2).
# "trend": o que significa um valor mais alto vs. mais baixo desta métrica em
# concreto - complementa (não substitui) o impacto puramente mecânico de
# subir/descer o threshold dado o operador escolhido, que é genérico e
# calculado no frontend (StrategyEditor.tsx) para qualquer métrica.
INDICATORS: dict[str, dict] = {
    "PRICE_CLOSE": {
        "kind": "price", "fn": latest_close, "lookback_days": 1,
        "description": "Último preço de fecho da ação.",
        "unit": "preço na moeda nativa da ação (ex: 185.30)",
        "trend": "Não tem 'bom' ou 'mau' por si só - serve para comparar com outro preço ou média (ex: SMA_200).",
    },
    "RSI_14": {
        "kind": "price", "fn": lambda c: calc_rsi(c, 14), "lookback_days": 30,
        "description": "Índice de força relativa (14 dias). Abaixo de 30 costuma indicar "
                       "sobrevendido; acima de 70, sobrecomprado.",
        "unit": "pontos, escala de 0 a 100 (ex: 30)",
        "trend": "Mais alto = mais sobrecomprado (pode estar 'caro' no curto prazo); mais baixo = mais sobrevendido (pode estar 'barato').",
    },
    "SMA_50": {
        "kind": "price", "fn": lambda c: calc_sma(c, 50), "lookback_days": 60,
        "description": "Média móvel simples de 50 dias — tendência de curto/médio prazo.",
        "unit": "preço na moeda nativa da ação (ex: 185.30)",
        "trend": "Preço a negociar acima da média = tendência de subida; abaixo = tendência de descida.",
    },
    "SMA_200": {
        "kind": "price", "fn": lambda c: calc_sma(c, 200), "lookback_days": 210,
        "description": "Média móvel simples de 200 dias — tendência de longo prazo.",
        "unit": "preço na moeda nativa da ação (ex: 185.30)",
        "trend": "Preço a negociar acima da média = tendência de subida de longo prazo; abaixo = tendência de descida.",
    },
    "PE_RATIO": {
        "kind": "fundamental", "field": "pe_ratio", "lookback_days": 0,
        "description": "Rácio preço/lucro (P/E). Quanto mais baixo, mais 'barata' a ação "
                       "face aos lucros atuais.",
        "unit": "rácio, número simples (ex: 15 = paga-se 15x o lucro anual por ação)",
        "trend": "Mais alto = paga-se mais por cada euro/dólar de lucro (pode refletir expectativa de crescimento, ou estar caro); mais baixo = mais 'barata' face aos lucros atuais.",
    },
    "DIVIDEND_YIELD": {
        "kind": "fundamental", "field": "dividend_yield", "lookback_days": 0,
        "description": "Rendimento em dividendos, como fração do preço da ação (ex: 0.02 = 2%).",
        "unit": "fração do preço, NÃO percentagem (ex: escreve 0.02 para 2%, não 2)",
        "trend": "Mais alto = paga mais dividendo por ano face ao preço atual; mais baixo (ou 0) = paga pouco ou nenhum dividendo.",
    },
    "EPS": {
        "kind": "fundamental", "field": "eps", "lookback_days": 0,
        "description": "Lucro por ação (EPS), últimos 12 meses. Quanto maior, mais lucro "
                       "gerado por cada ação.",
        "unit": "valor monetário por ação, na moeda nativa (ex: 6.10)",
        "trend": "Mais alto = mais lucro gerado por cada ação; mais baixo ou negativo = menos lucro (ou prejuízo).",
    },
    "DEBT_TO_EQUITY": {
        "kind": "fundamental", "field": "debt_to_equity", "lookback_days": 0,
        "description": "Rácio dívida/capital próprio. Quanto mais alto, maior a alavancagem "
                       "financeira da empresa.",
        "unit": "rácio, número simples (ex: 1.5 = dívida é 1.5x o capital próprio)",
        "trend": "Mais alto = mais dívida face ao capital próprio (mais alavancagem/risco financeiro); mais baixo = empresa menos endividada.",
    },
    "MARKET_CAP": {
        "kind": "fundamental", "field": "market_cap", "lookback_days": 0, "scale": 1_000_000_000,
        "description": "Capitalização de mercado, em mil milhões de USD (ex: 500 = $500B). "
                       "Indica a dimensão da empresa.",
        "unit": "mil milhões de USD, não o valor absoluto (ex: escreve 500 para $500 mil milhões)",
        "trend": "Mais alto = empresa maior/mais estabelecida (tipicamente menos volátil); mais baixo = empresa mais pequena (potencialmente mais volátil).",
    },
}
