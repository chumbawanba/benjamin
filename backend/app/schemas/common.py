import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

VALID_OPERATORS = {"<", ">", "<=", ">=", "==", "between"}
VALID_DIRECTIONS = {"buy_signal", "sell_signal"}


# ---- Auth ----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


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

    model_config = {"from_attributes": True}


class WatchlistReorderIn(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1)


class TickerSearchResult(BaseModel):
    ticker: str
    name: str | None
    exchange: str | None


class NewsItemOut(BaseModel):
    ticker: str
    headline: str | None
    summary: str | None
    url: str | None
    source: str | None
    published_at: datetime | None


# ---- Strategies ----
class StrategyTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
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


class StrategyTemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
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
