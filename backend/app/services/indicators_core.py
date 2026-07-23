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


def calc_price_vs_sma(closes: pd.Series, period: int) -> float | None:
    """% de diferença entre o último fecho e a SMA(period) - ex: 5.0 = preço
    5% acima da média, -3.0 = preço 3% abaixo. Ao contrário de PRICE_CLOSE ou
    SMA_50/SMA_200 (valores absolutos, na moeda da ação), esta métrica é
    adimensional/percentual: um threshold como '> 0' funciona igual para
    qualquer ação, independentemente da escala de preço (ver conversa com o
    utilizador - SMA_200 sozinho não é comparável entre ações com preços
    muito diferentes, ex: 20 vs 2000)."""
    sma = calc_sma(closes, period)
    if sma is None or sma == 0:
        return None
    last = latest_close(closes)
    if last is None:
        return None
    return (last - sma) / sma * 100


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
        "description": "Último preço de fecho da ação. Valor absoluto - um threshold fixo "
                       "só faz sentido para uma ação específica, não numa estratégia aplicada "
                       "a várias ações com preços muito diferentes.",
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
        "description": "Média móvel simples de 50 dias — tendência de curto/médio prazo. Valor "
                       "absoluto (preço) - numa estratégia com várias ações de preços muito "
                       "diferentes, considera usar PRICE_VS_SMA_50 em vez desta.",
        "unit": "preço na moeda nativa da ação (ex: 185.30)",
        "trend": "Preço a negociar acima da média = tendência de subida; abaixo = tendência de descida.",
    },
    "SMA_200": {
        "kind": "price", "fn": lambda c: calc_sma(c, 200), "lookback_days": 210,
        "description": "Média móvel simples de 200 dias — tendência de longo prazo. Valor "
                       "absoluto (preço) - numa estratégia com várias ações de preços muito "
                       "diferentes, considera usar PRICE_VS_SMA_200 em vez desta.",
        "unit": "preço na moeda nativa da ação (ex: 185.30)",
        "trend": "Preço a negociar acima da média = tendência de subida de longo prazo; abaixo = tendência de descida.",
    },
    "PRICE_VS_SMA_50": {
        "kind": "price", "fn": lambda c: calc_price_vs_sma(c, 50), "lookback_days": 60,
        "description": "Diferença entre o preço atual e a SMA_50, em percentagem — versão "
                       "relativa da SMA_50, comparável entre ações com preços muito diferentes "
                       "(ao contrário de SMA_50/SMA_200/PRICE_CLOSE, que são valores absolutos).",
        "unit": "percentagem (ex: 5 = preço 5% acima da média; -3 = 3% abaixo)",
        "trend": "Mais alto = preço bem acima da média de 50 dias (tendência de subida de curto/médio prazo); mais baixo/negativo = preço abaixo da média (tendência de descida). Perto de 0 = preço colado à média.",
    },
    "PRICE_VS_SMA_200": {
        "kind": "price", "fn": lambda c: calc_price_vs_sma(c, 200), "lookback_days": 210,
        "description": "Diferença entre o preço atual e a SMA_200, em percentagem — versão "
                       "relativa da SMA_200, comparável entre ações com preços muito diferentes "
                       "(ao contrário de SMA_50/SMA_200/PRICE_CLOSE, que são valores absolutos). "
                       "É esta a métrica recomendada para critérios de estratégia baseados em "
                       "média móvel, quando a estratégia se aplica a mais do que uma ação.",
        "unit": "percentagem (ex: 5 = preço 5% acima da média; -3 = 3% abaixo)",
        "trend": "Mais alto = preço bem acima da média de 200 dias (tendência de subida de longo prazo); mais baixo/negativo = preço abaixo da média (tendência de descida). Perto de 0 = preço colado à média.",
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
    "ROE": {
        "kind": "fundamental", "field": "roe", "lookback_days": 0,
        "description": "Rentabilidade do capital próprio (ROE) — lucro gerado por cada euro/"
                       "dólar de capital próprio investido na empresa, últimos 12 meses.",
        "unit": "percentagem (ex: 15 = ROE de 15%, não 0.15)",
        "trend": "Mais alto = empresa gera mais lucro com o capital próprio que tem (tipicamente sinal de qualidade); mais baixo = usa o capital de forma menos eficiente.",
    },
    "NET_MARGIN": {
        "kind": "fundamental", "field": "net_margin", "lookback_days": 0,
        "description": "Margem líquida — que fração de cada euro/dólar de receita sobra como "
                       "lucro, depois de todos os custos.",
        "unit": "percentagem (ex: 20 = margem líquida de 20%, não 0.20)",
        "trend": "Mais alto = empresa converte mais receita em lucro (tipicamente sinal de qualidade/poder de precificação); mais baixo = margens mais apertadas.",
    },
    "REVENUE_GROWTH": {
        "kind": "fundamental", "field": "revenue_growth", "lookback_days": 0,
        "description": "Crescimento da receita, ano a ano (YoY), últimos 12 meses.",
        "unit": "percentagem (ex: 10 = receita cresceu 10% face ao ano anterior)",
        "trend": "Mais alto = negócio a crescer mais depressa; mais baixo ou negativo = crescimento a abrandar ou receita a encolher.",
    },
    "GROSS_MARGIN": {
        "kind": "fundamental", "field": "gross_margin", "lookback_days": 0,
        "description": "Margem bruta — que fração de cada euro/dólar de receita sobra depois "
                       "do custo direto de produzir o produto/serviço, antes de despesas "
                       "operacionais, juros e impostos.",
        "unit": "percentagem (ex: 40 = margem bruta de 40%, não 0.40)",
        "trend": "Mais alto = mais poder de precificação ou custos de produção mais baixos face à concorrência; mais baixo = negócio mais dependente de volume para ser rentável.",
    },
    "OPERATING_MARGIN": {
        "kind": "fundamental", "field": "operating_margin", "lookback_days": 0,
        "description": "Margem operacional — que fração de cada euro/dólar de receita sobra "
                       "depois de todos os custos operacionais (produção + despesas do negócio), "
                       "antes de juros e impostos.",
        "unit": "percentagem (ex: 20 = margem operacional de 20%, não 0.20)",
        "trend": "Mais alto = negócio operacionalmente mais eficiente; mais baixo = mais custos operacionais a comer a receita.",
    },
    "EPS_GROWTH": {
        "kind": "fundamental", "field": "eps_growth", "lookback_days": 0,
        "description": "Crescimento do lucro por ação (EPS), ano a ano (YoY), últimos 12 "
                       "meses — usado por estratégias tipo CAN SLIM, que valorizam aceleração "
                       "de lucros mais do que o nível absoluto do EPS.",
        "unit": "percentagem (ex: 25 = EPS cresceu 25% face ao ano anterior)",
        "trend": "Mais alto = lucro por ação a crescer mais depressa; mais baixo ou negativo = crescimento de lucros a abrandar ou a encolher.",
    },
    "DIVIDEND_GROWTH_5Y": {
        "kind": "fundamental", "field": "dividend_growth_5y", "lookback_days": 0,
        "description": "Taxa de crescimento anual do dividendo, média dos últimos 5 anos — "
                       "usada por estratégias de Dividend Growth, que preferem dividendo a "
                       "crescer de forma consistente a um yield elevado mas estagnado.",
        "unit": "percentagem (ex: 8 = dividendo cresceu em média 8%/ano nos últimos 5 anos)",
        "trend": "Mais alto = empresa a aumentar o dividendo de forma consistente (tipicamente sinal de saúde financeira); mais baixo ou negativo = dividendo estagnado ou a encolher.",
    },
}
