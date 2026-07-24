"""Síntese visual por ação: agrupa um subconjunto dos indicadores em 4
categorias (valuation, momentum, crescimento, rendibilidade) com uma
classificação simples favorável/neutro/desfavorável, para dar uma leitura
rápida sem ter de percorrer a grelha inteira de indicadores.

IMPORTANTE - isto é um heurístico simplificado, não a recomendação BUY/SELL/
HOLD da app (essa vem de agent_core.py, calculada a partir dos critérios e
pesos que o utilizador configurou na estratégia). A síntese aqui usa
thresholds fixos, iguais para todas as ações e estratégias - útil para uma
primeira leitura, mas dois investidores com estilos diferentes (growth vs.
value, por exemplo) podem legitimamente discordar destes thresholds. Não é
aconselhamento financeiro.

Ficam de fora do scoring (continuam só na grelha "Indicadores" existente,
sem categoria/classificação):
- DIVIDEND_YIELD, DIVIDEND_GROWTH_5Y: "bom" ou "mau" depende do estilo do
  investidor (growth vs. income), não há um threshold universal razoável.
- DEBT_TO_EQUITY: é uma métrica de risco/estrutura de capital, não encaixa
  bem em nenhuma das 4 categorias sem forçar a categorização.
- MARKET_CAP, EPS, PRICE_CLOSE, SMA_50, SMA_200: valores absolutos/
  informativos, sem uma leitura direta de "favorável"/"desfavorável".
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

Classification = Literal["favoravel", "neutro", "desfavoravel", "misto"]

CATEGORY_LABELS: dict[str, str] = {
    "valuation": "Valuation",
    "momentum": "Momentum",
    "growth": "Crescimento",
    "profitability": "Rendibilidade",
}
CATEGORY_ORDER = ["valuation", "momentum", "growth", "profitability"]


def _bucket_higher_better(value: float, bad_below: float, good_above: float) -> Classification:
    if value >= good_above:
        return "favoravel"
    if value <= bad_below:
        return "desfavoravel"
    return "neutro"


def _bucket_lower_better(value: float, good_below: float, bad_above: float) -> Classification:
    if value <= good_below:
        return "favoravel"
    if value >= bad_above:
        return "desfavoravel"
    return "neutro"


def _classify_rsi(value: float) -> Classification:
    # Segue a mesma leitura já usada nas estratégias de referência da app
    # (ver StrategyLibrary.tsx): RSI < 30 = sobrevendido, tratado como sinal
    # de entrada (favorável); RSI > 70 = sobrecomprado (desfavorável).
    if value <= 30:
        return "favoravel"
    if value >= 70:
        return "desfavoravel"
    return "neutro"


# Thresholds documentados em cada regra - números redondos, escolhidos como
# ponto de partida razoável (ex: PE < 15 "barata", > 30 "cara"; ROE > 15%
# "boa rentabilidade", < 5% "fraca"). Podem ser afinados no futuro, mas
# ficam centralizados aqui para serem fáceis de encontrar e ajustar.
SYNTHESIS_RULES: dict[str, dict] = {
    "PE_RATIO": {
        "category": "valuation", "short_label": "PE",
        "classify": lambda v: _bucket_lower_better(v, good_below=15, bad_above=30),
        "format": lambda v: f"{v:.1f}",
    },
    "RSI_14": {
        "category": "momentum", "short_label": "RSI",
        "classify": _classify_rsi,
        "format": lambda v: f"{v:.0f}",
    },
    "PRICE_VS_SMA_50": {
        "category": "momentum", "short_label": "vs SMA 50",
        "classify": lambda v: _bucket_higher_better(v, bad_below=-5, good_above=5),
        "format": lambda v: f"{v:+.0f}%",
    },
    "PRICE_VS_SMA_200": {
        "category": "momentum", "short_label": "vs SMA 200",
        "classify": lambda v: _bucket_higher_better(v, bad_below=-5, good_above=5),
        "format": lambda v: f"{v:+.0f}%",
    },
    "REVENUE_GROWTH": {
        "category": "growth", "short_label": "Receita",
        "classify": lambda v: _bucket_higher_better(v, bad_below=0, good_above=10),
        "format": lambda v: f"{v:+.1f}%",
    },
    "EPS_GROWTH": {
        "category": "growth", "short_label": "EPS",
        "classify": lambda v: _bucket_higher_better(v, bad_below=0, good_above=10),
        "format": lambda v: f"{v:+.0f}%",
    },
    "ROE": {
        "category": "profitability", "short_label": "ROE",
        "classify": lambda v: _bucket_higher_better(v, bad_below=5, good_above=15),
        "format": lambda v: f"{v:.1f}%",
    },
    "NET_MARGIN": {
        "category": "profitability", "short_label": "margem líquida",
        "classify": lambda v: _bucket_higher_better(v, bad_below=5, good_above=15),
        "format": lambda v: f"{v:.0f}%",
    },
    "GROSS_MARGIN": {
        "category": "profitability", "short_label": "margem bruta",
        "classify": lambda v: _bucket_higher_better(v, bad_below=20, good_above=40),
        "format": lambda v: f"{v:.0f}%",
    },
    "OPERATING_MARGIN": {
        "category": "profitability", "short_label": "margem operacional",
        "classify": lambda v: _bucket_higher_better(v, bad_below=5, good_above=15),
        "format": lambda v: f"{v:.0f}%",
    },
}


@dataclass
class CategorySynthesis:
    category: str
    label: str
    classification: Classification | None  # None = sem dados suficientes
    reason: str | None


@dataclass
class StockSynthesis:
    score: float | None  # 0-100, None se não houver nenhum indicador avaliável
    categories: list[CategorySynthesis]


def compute_synthesis(values: dict[str, float | None]) -> StockSynthesis:
    """values: {indicator_key: valor} - tipicamente os mesmos valores já
    calculados para a grelha "Indicadores" da StockDetail (ver
    watchlist.py::watchlist_item_detail), reaproveitados aqui sem nenhum
    pedido extra à BD ou à Finnhub."""
    by_category: dict[str, list[tuple[str, str, Classification]]] = defaultdict(list)
    counts = {"favoravel": 0, "neutro": 0, "desfavoravel": 0}
    total = 0

    for key, rule in SYNTHESIS_RULES.items():
        value = values.get(key)
        if value is None:
            continue
        classification = rule["classify"](value)
        by_category[rule["category"]].append((rule["short_label"], rule["format"](value), classification))
        counts[classification] += 1
        total += 1

    categories: list[CategorySynthesis] = []
    for cat in CATEGORY_ORDER:
        entries = by_category.get(cat, [])
        if not entries:
            categories.append(CategorySynthesis(cat, CATEGORY_LABELS[cat], None, None))
            continue
        classes = {c for _, _, c in entries}
        if "desfavoravel" in classes and "favoravel" not in classes:
            cat_class: Classification = "desfavoravel"
        elif "favoravel" in classes and "desfavoravel" not in classes:
            cat_class = "favoravel"
        elif "favoravel" in classes and "desfavoravel" in classes:
            cat_class = "misto"
        else:
            cat_class = "neutro"
        reason = ", ".join(f"{label} {formatted}" for label, formatted, _ in entries)
        categories.append(CategorySynthesis(cat, CATEGORY_LABELS[cat], cat_class, reason))

    score = round(100 * (counts["favoravel"] + 0.5 * counts["neutro"]) / total) if total > 0 else None
    return StockSynthesis(score=score, categories=categories)
