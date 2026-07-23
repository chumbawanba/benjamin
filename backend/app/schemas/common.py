import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

VALID_OPERATORS = {"<", ">", "<=", ">=", "==", "between"}
VALID_DIRECTIONS = {"buy_signal", "sell_signal"}
VALID_HORIZONS = {"short_term", "medium_term", "long_term"}


# ---- Auth ----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None
    # Obrigatório (validado no router, não aqui, para dar uma mensagem clara -
    # ver auth.py) - false ou omitido dão 422 antes de criar a conta.
    accepted_terms: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Waitlist ----
class WaitlistIn(BaseModel):
    email: EmailStr
    # Obrigatório (validado no router - ver routers/waitlist.py), mesmo padrão de RegisterIn.
    accepted_terms: bool = False


# ---- Watchlist ----
class WatchlistItemIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    notes: str | None = None
    target_buy_price: Decimal | None = None
    target_sell_price: Decimal | None = None


class StockOut(BaseModel):
    id: uuid.UUID
    ticker: str
    name: str | None
    currency: str | None
    sector: str | None = None
    asset_type: str = "stock"
    exchange: str | None = None
    # Última vez que se tentou obter a cotação intradiária (Finnhub /quote,
    # sucesso ou falha) - frontend usa para mostrar "atualizado há X min" (ver
    # market_data.ensure_fresh/QUOTE_REFRESH_COOLDOWN).
    last_quote_at: datetime | None = None

    model_config = {"from_attributes": True}


class EvaluationSummaryOut(BaseModel):
    id: uuid.UUID
    run_at: datetime
    buy_score: Decimal
    sell_score: Decimal
    recommendation: str
    price_at_evaluation: Decimal | None

    model_config = {"from_attributes": True}


class WatchlistItemOut(BaseModel):
    id: uuid.UUID
    stock: StockOut
    notes: str | None
    target_buy_price: Decimal | None
    target_sell_price: Decimal | None
    added_at: datetime
    display_order: int
    latest_evaluation: EvaluationSummaryOut | None = None
    last_price: Decimal | None = None
    price_change_pct: Decimal | None = None

    model_config = {"from_attributes": True}


class WatchlistReorderIn(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1)


# ---- Detalhe de ação (página StockDetail) ----
class PricePointOut(BaseModel):
    date: date
    close: Decimal | None
    sma_200: float | None = None  # float de propósito (não Decimal) - ver OptimizeItemOut

    model_config = {"from_attributes": True}


class IndicatorValueOut(BaseModel):
    key: str
    value: float | None
    description: str | None


class FundamentalsOut(BaseModel):
    date: date
    pe_ratio: Decimal | None
    eps: Decimal | None
    debt_to_equity: Decimal | None
    dividend_yield: Decimal | None
    market_cap: int | None
    revenue_growth: Decimal | None
    net_margin: Decimal | None
    roe: Decimal | None
    current_ratio: Decimal | None
    gross_margin: Decimal | None = None
    operating_margin: Decimal | None = None
    eps_growth: Decimal | None = None
    dividend_growth_5y: Decimal | None = None

    model_config = {"from_attributes": True}


class EvaluationCriterionOut(BaseModel):
    name: str
    metric: str
    operator: str
    threshold_value: Decimal | None
    threshold_value_max: Decimal | None
    weight: Decimal
    direction: str
    observed_value: Decimal | None
    passed: bool | None
    contribution: Decimal


class StockDetailOut(BaseModel):
    stock: StockOut
    last_price: Decimal | None
    price_change_pct: Decimal | None
    price_history: list[PricePointOut]
    indicators: list[IndicatorValueOut]
    fundamentals: FundamentalsOut | None
    latest_evaluation: EvaluationSummaryOut | None
    strategy_name: str | None
    criteria: list[EvaluationCriterionOut]


class TickerSearchResult(BaseModel):
    ticker: str
    name: str | None
    type: str | None = None
    market_hint: str | None = None


class SuggestionOut(BaseModel):
    ticker: str
    based_on: str  # ticker da watchlist que originou a sugestão (mesma indústria)


class NewsItemOut(BaseModel):
    ticker: str
    headline: str | None
    summary: str | None
    url: str | None
    source: str | None
    published_at: datetime | None


class AnalystSummaryOut(BaseModel):
    summary: str | None
    generated_at: datetime | None


class AnalystPromptOut(BaseModel):
    prompt: str
    is_default: bool


class AnalystPromptIn(BaseModel):
    prompt: str | None = None  # None ou "" repõe a predefinição


# ---- Analyst: perguntas com contexto ("Perguntar ao Benjamin") ----
class AnalystChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AnalystAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    # histórico da conversa até agora, mantido no frontend (sem tabela na BD) -
    # limitado para controlar custo/latência do pedido à OpenAI.
    history: list[AnalystChatMessageIn] = Field(default_factory=list, max_length=20)


class AnalystAskOut(BaseModel):
    answer: str


# ---- Portfolio (posições reais, distinto da watchlist) ----
class PositionIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    avg_cost: Decimal = Field(gt=0)


class PositionUpdateIn(BaseModel):
    quantity: Decimal = Field(gt=0)
    avg_cost: Decimal = Field(gt=0)


class PositionOut(BaseModel):
    id: uuid.UUID
    stock: StockOut
    quantity: Decimal
    avg_cost: Decimal
    cost_total: Decimal
    last_price: Decimal | None
    price_change_pct: Decimal | None
    market_value: Decimal | None
    unrealized_pl: Decimal | None
    unrealized_pl_pct: Decimal | None
    updated_at: datetime
    # Valores convertidos para User.preferred_currency (ver app/services/fx.py) -
    # None se a taxa de câmbio não estiver disponível. display_currency é sempre
    # a moeda preferida atual, mesmo quando a conversão falha.
    display_currency: str
    cost_total_converted: Decimal | None
    market_value_converted: Decimal | None
    unrealized_pl_converted: Decimal | None


class PortfolioCurrencyOut(BaseModel):
    currency: str


class PortfolioCurrencyIn(BaseModel):
    currency: str = Field(min_length=3, max_length=3)


class FxRateOut(BaseModel):
    base_currency: str
    quote_currency: str
    rate: Decimal
    date: date


# ---- Strategies ----
class StrategyTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    horizon: str | None = None
    is_active: bool = True


class StrategyItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    metric: str
    operator: str
    threshold_value: Decimal | None = None
    threshold_value_max: Decimal | None = None
    weight: Decimal = Decimal("1.0")
    direction: str
    is_active: bool = True
    display_order: int | None = None


class StrategyItemOut(StrategyItemIn):
    id: uuid.UUID
    model_config = {"from_attributes": True}


class OptimizeItemOut(BaseModel):
    """Usa float (não Decimal) de propósito: vem diretamente do backtest_core,
    que trabalha com floats, e evita a serialização de Decimal como string em
    JSON (ver PriceChange.tsx) — o frontend chama .toFixed() diretamente
    nestes campos."""
    name: str
    metric: str
    operator: str
    threshold_value: float | None
    threshold_value_max: float | None
    weight: float
    direction: str


class OptimizeResultOut(BaseModel):
    items: list[OptimizeItemOut]
    backtest_return_pct: float
    buy_and_hold_return_pct: float | None
    stocks_evaluated: int


class BacktestPointOut(BaseModel):
    """Ponto de preço para o gráfico de backtest - float de propósito, mesma
    razão da OptimizeItemOut (vem do backtest_core, que trabalha em float)."""
    date: date
    close: float


class BacktestTradeOut(BaseModel):
    date: date | None
    action: str  # "BUY" | "SELL"
    price: float


class BacktestChartOut(BaseModel):
    points: list[BacktestPointOut]
    trades: list[BacktestTradeOut]
    return_pct: float
    buy_and_hold_return_pct: float | None
    warmup_days: int


class StrategyTemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    horizon: str | None
    is_active: bool
    items: list[StrategyItemOut] = []

    model_config = {"from_attributes": True}


# ---- Evaluations ----
class RunEvaluationIn(BaseModel):
    template_id: uuid.UUID
    stock_id: uuid.UUID | None = None


class EvaluationDetailOut(BaseModel):
    strategy_item_id: uuid.UUID
    observed_value: Decimal | None
    passed: bool | None
    contribution: Decimal

    model_config = {"from_attributes": True}


class EvaluationOut(EvaluationSummaryOut):
    stock_id: uuid.UUID
    strategy_template_id: uuid.UUID
    details: list[EvaluationDetailOut] = []


# ---- Sinais agrupados por estratégia (Overview) ----
class StrategySignalOut(BaseModel):
    stock: StockOut
    recommendation: str
    buy_score: Decimal
    sell_score: Decimal
    run_at: datetime
    last_price: Decimal | None
    price_change_pct: Decimal | None


class StrategySignalGroupOut(BaseModel):
    strategy_id: uuid.UUID
    strategy_name: str
    horizon: str | None
    signals: list[StrategySignalOut]
