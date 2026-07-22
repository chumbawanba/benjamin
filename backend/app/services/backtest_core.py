"""Motor de backtest e otimizador de estratégias. Puro - sem acesso a BD,
testável isoladamente (como agent_core.py e indicators_core.py).

Simula, dia a dia, o que a estratégia teria feito num histórico de preços já
carregado, reutilizando o mesmo motor de scoring do agente real
(agent_core.compute_evaluation) para que o resultado do backtest seja
consistente com uma avaliação ao vivo.

Limitações conhecidas (documentadas para o utilizador na UI):
- Fundamentais (P/E, EPS, etc.) são tratados como constantes ao longo de todo
  o período, usando o valor mais recente conhecido — a app só guarda o
  "snapshot" mais recente de fundamentais, não um histórico diário.
- Só indicadores com escala comparável entre ações diferentes (RSI, rácios,
  PRICE_VS_SMA_50/200) entram no conjunto de candidatos do otimizador;
  preço/médias móveis absolutos (SMA_50, SMA_200, PRICE_CLOSE) ficam de fora
  porque o nível de preço não é comparável entre ações distintas na mesma
  estratégia — usa-se a versão relativa (% face à média) em vez disso.
"""
from dataclasses import dataclass, field

import pandas as pd

from app.services.agent_core import compute_evaluation
from app.services.indicators_core import INDICATORS

WARMUP_DAYS = 30
MAX_ITEMS = 6
INITIAL_CAPITAL = 1000.0
MIN_HISTORY_DAYS = 60

CANDIDATE_SPECS: list[tuple[str, str, str, list[float]]] = [
    ("RSI_14", "buy_signal", "<", [20, 25, 30, 35, 40]),
    ("RSI_14", "sell_signal", ">", [60, 65, 70, 75, 80]),
    ("PE_RATIO", "buy_signal", "<", [10, 15, 20, 25, 30]),
    ("PE_RATIO", "sell_signal", ">", [25, 30, 35, 40, 50]),
    ("DEBT_TO_EQUITY", "buy_signal", "<", [0.5, 1.0, 1.5, 2.0]),
    ("DEBT_TO_EQUITY", "sell_signal", ">", [1.5, 2.0, 2.5, 3.0]),
    ("DIVIDEND_YIELD", "buy_signal", ">", [0.005, 0.01, 0.015, 0.02, 0.03]),
    ("EPS", "buy_signal", ">", [0, 1, 2]),
    ("MARKET_CAP", "buy_signal", ">", [1, 10, 50, 200]),
    ("PRICE_VS_SMA_50", "buy_signal", ">", [0, 2, 5]),
    ("PRICE_VS_SMA_50", "sell_signal", "<", [-5, -2, 0]),
    ("PRICE_VS_SMA_200", "buy_signal", ">", [0, 2, 5]),
    ("PRICE_VS_SMA_200", "sell_signal", "<", [-5, -2, 0]),
    ("ROE", "buy_signal", ">", [10, 15, 20]),
    ("NET_MARGIN", "buy_signal", ">", [5, 10, 15, 20]),
    ("REVENUE_GROWTH", "buy_signal", ">", [0, 5, 10]),
]


@dataclass
class StockSeries:
    ticker: str
    closes: list[float]
    fundamentals: dict[str, float | None]
    indicator_frame: dict[str, list[float | None]] = field(default_factory=dict)
    dates: list = field(default_factory=list)  # list[datetime.date], alinhado 1:1 com closes


def _to_list(series: pd.Series) -> list[float | None]:
    return [None if pd.isna(v) else float(v) for v in series]


def _expanding_indicator_frame(closes: list[float]) -> dict[str, list[float | None]]:
    """Para cada indicador price-kind, calcula o valor com o histórico
    disponível até cada dia (expanding window) — replica o que uma avaliação
    real teria visto nesse dia, sem espreitar o futuro.

    Vetorizado sobre a série inteira (uma passagem), em vez de recalcular
    RSI/SMA do zero a cada dia com fatias crescentes — essa abordagem ingénua
    é O(n²) e demorava dezenas de segundos com ~365 dias × várias ações
    (chegou a estourar o timeout do browser). `rolling().mean()` e
    `ewm(adjust=False)` já são causais por construção (o valor na linha i só
    depende de linhas <= i), logo dão exatamente o mesmo resultado que
    indicators_core.calc_sma/calc_rsi chamados dia a dia, mas em O(n).

    Só cobre os indicadores price-kind vetorizáveis conhecidos (PRICE_CLOSE,
    RSI_14, SMA_50, SMA_200, PRICE_VS_SMA_50, PRICE_VS_SMA_200); qualquer
    indicador price-kind novo cai no fallback lento — não fica silenciosamente
    de fora, mas é preciso vetorizá-lo aqui para manter o otimizador rápido.
    """
    s = pd.Series(closes, dtype=float)
    frame: dict[str, list[float | None]] = {}
    handled: set[str] = set()

    if "PRICE_CLOSE" in INDICATORS:
        frame["PRICE_CLOSE"] = _to_list(s)
        handled.add("PRICE_CLOSE")
    sma_50 = s.rolling(50).mean()
    sma_200 = s.rolling(200).mean()
    if "SMA_50" in INDICATORS:
        frame["SMA_50"] = _to_list(sma_50)
        handled.add("SMA_50")
    if "SMA_200" in INDICATORS:
        frame["SMA_200"] = _to_list(sma_200)
        handled.add("SMA_200")
    if "PRICE_VS_SMA_50" in INDICATORS:
        # .where(sma_50 != 0) evita inf quando a média é 0 (ação sem valor) -
        # mesma regra de segurança do cálculo não vetorizado (calc_price_vs_sma).
        frame["PRICE_VS_SMA_50"] = _to_list(((s - sma_50) / sma_50 * 100).where(sma_50 != 0))
        handled.add("PRICE_VS_SMA_50")
    if "PRICE_VS_SMA_200" in INDICATORS:
        frame["PRICE_VS_SMA_200"] = _to_list(((s - sma_200) / sma_200 * 100).where(sma_200 != 0))
        handled.add("PRICE_VS_SMA_200")
    if "RSI_14" in INDICATORS:
        period = 14
        delta = s.diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100.0 - 100.0 / (1.0 + rs)
        rsi = rsi.where(avg_loss != 0, 100.0)
        rsi = rsi.where(avg_gain.notna() & avg_loss.notna())
        frame["RSI_14"] = _to_list(rsi)
        handled.add("RSI_14")

    for key, spec in INDICATORS.items():
        if spec["kind"] != "price" or key in handled:
            continue
        fn = spec["fn"]
        frame[key] = [fn(s.iloc[: i + 1]) for i in range(len(s))]  # fallback lento
    return frame


def build_stock_series(
    ticker: str, closes: list[float], fundamentals: dict[str, float | None], dates: list | None = None,
) -> StockSeries:
    return StockSeries(
        ticker=ticker, closes=closes, fundamentals=fundamentals,
        indicator_frame=_expanding_indicator_frame(closes),
        dates=dates or [],
    )


def fundamentals_to_observed(row) -> dict[str, float | None]:
    """Converte uma FundamentalsSnapshot (ou None) num dict {indicador: valor},
    aplicando a mesma escala usada nas avaliações ao vivo (ver indicators.py)."""
    observed: dict[str, float | None] = {}
    for key, spec in INDICATORS.items():
        if spec["kind"] != "fundamental":
            continue
        value = getattr(row, spec["field"], None) if row is not None else None
        if value is not None:
            value = float(value)
            if spec.get("scale"):
                value = value / spec["scale"]
        observed[key] = value
    return observed


def simulate(series: StockSeries, items: list[dict], warmup_days: int = WARMUP_DAYS,
             capital: float = INITIAL_CAPITAL, record_trades: bool = False) -> dict:
    """Compra ao 1º sinal BUY (todo o capital disponível), vende ao 1º sinal
    SELL seguinte (posição toda). Sem alavancagem, sem custos de transação.

    `record_trades=False` por omissão porque o otimizador chama isto milhares
    de vezes (greedy search sobre CANDIDATE_SPECS) e não precisa da lista de
    eventos — só quem quer desenhar um gráfico de compras/vendas passa True."""
    shares, cash, trades = 0.0, capital, 0
    trade_events: list[dict] = []
    n = len(series.closes)
    start = min(warmup_days, max(n - 1, 0))
    for i in range(start, n):
        observed = dict(series.fundamentals)
        for key, values in series.indicator_frame.items():
            observed[key] = values[i]
        result = compute_evaluation(items, observed)
        price = series.closes[i]
        if result.recommendation == "BUY" and shares == 0 and price:
            shares, cash = cash / price, 0.0
            trades += 1
            if record_trades:
                trade_events.append({
                    "date": series.dates[i] if series.dates else None, "action": "BUY", "price": price,
                })
        elif result.recommendation == "SELL" and shares > 0:
            cash, shares = shares * price, 0.0
            trades += 1
            if record_trades:
                trade_events.append({
                    "date": series.dates[i] if series.dates else None, "action": "SELL", "price": price,
                })
    final_price = series.closes[-1] if series.closes else 0.0
    final_value = cash + shares * final_price
    return_pct = round((final_value / capital - 1) * 100, 2) if capital else 0.0
    out = {"return_pct": return_pct, "trades": trades}
    if record_trades:
        out["trade_events"] = trade_events
    return out


def buy_and_hold_return(series: StockSeries, warmup_days: int = WARMUP_DAYS) -> float | None:
    n = len(series.closes)
    if n < 2:
        return None
    # min(warmup_days, n - 2) garante um start estritamente antes do último
    # índice (n - 1) — com histórico curto, `min(warmup_days, n - 1)` podia
    # colapsar start no próprio último dia, dando um "retorno" de 0% falso
    # em vez de admitir que não há histórico suficiente para comparar.
    start = min(warmup_days, n - 2)
    if start < 0 or not series.closes[start]:
        return None
    return round((series.closes[-1] / series.closes[start] - 1) * 100, 2)


def _avg_return(all_series: list[StockSeries], items: list[dict]) -> float:
    if not all_series:
        return 0.0
    returns = [simulate(s, items)["return_pct"] for s in all_series]
    return sum(returns) / len(returns)


def optimize(all_series: list[StockSeries]) -> dict:
    """Seleção greedy (forward selection): parte de um conjunto vazio de
    critérios e, a cada passo, adiciona o candidato — de entre
    CANDIDATE_SPECS — que mais melhora o retorno médio simulado em toda a
    watchlist, até MAX_ITEMS critérios ou até nenhum candidato melhorar o
    resultado atual."""
    candidates = [
        {
            "name": f"{metric} {operator} {threshold}",
            "metric": metric, "operator": operator,
            "threshold_value": threshold, "threshold_value_max": None,
            "weight": 1.0, "direction": direction,
        }
        for metric, direction, operator, thresholds in CANDIDATE_SPECS
        for threshold in thresholds
    ]

    current: list[dict] = []
    current_return = _avg_return(all_series, current)
    used: set[int] = set()
    while len(current) < MAX_ITEMS:
        best = None
        best_return = current_return
        for idx, cand in enumerate(candidates):
            if idx in used:
                continue
            trial_return = _avg_return(all_series, current + [cand])
            if trial_return > best_return:
                best_return = trial_return
                best = (idx, cand)
        if best is None:
            break
        idx, cand = best
        used.add(idx)
        current.append(cand)
        current_return = best_return

    baseline_returns = [r for s in all_series if (r := buy_and_hold_return(s)) is not None]
    baseline_avg = round(sum(baseline_returns) / len(baseline_returns), 2) if baseline_returns else None

    return {
        "items": current,
        "backtest_return_pct": round(current_return, 2),
        "buy_and_hold_return_pct": baseline_avg,
        "stocks_evaluated": len(all_series),
    }
