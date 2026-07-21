// Espelha app/schemas/common.py do backend.

export interface Stock {
  id: string;
  ticker: string;
  name: string | null;
  currency: string | null;
}

export interface EvaluationSummary {
  id: string;
  run_at: string;
  buy_score: number;
  sell_score: number;
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  price_at_evaluation: number | null;
}

export interface WatchlistItem {
  id: string;
  stock: Stock;
  notes: string | null;
  target_buy_price: number | null;
  target_sell_price: number | null;
  added_at: string;
  display_order: number;
  latest_evaluation: EvaluationSummary | null;
  last_price: number | null;
  price_change_pct: number | null;
}

export type Direction = 'buy_signal' | 'sell_signal';

export interface StrategyItem {
  id: string;
  name: string;
  category: string | null;
  metric: string;
  operator: string;
  threshold_value: number | null;
  threshold_value_max: number | null;
  weight: number;
  direction: Direction;
  is_active: boolean;
  display_order: number | null;
}

export interface StrategyItemInput {
  name: string;
  category?: string | null;
  metric: string;
  operator: string;
  threshold_value?: number | null;
  threshold_value_max?: number | null;
  weight: number;
  direction: Direction;
  is_active?: boolean;
  display_order?: number | null;
}

export type Horizon = 'short_term' | 'medium_term' | 'long_term';

export interface StrategyTemplate {
  id: string;
  name: string;
  description: string | null;
  horizon: Horizon | null;
  is_active: boolean;
  items: StrategyItem[];
}

export interface EvaluationDetail {
  strategy_item_id: string;
  observed_value: number | null;
  passed: boolean | null;
  contribution: number;
}

export interface Evaluation extends EvaluationSummary {
  stock_id: string;
  strategy_template_id: string;
  details: EvaluationDetail[];
}

export interface TickerSearchResult {
  ticker: string;
  name: string | null;
  exchange: string | null;
}

export interface MetricInfo {
  key: string;
  kind: 'price' | 'fundamental';
  lookback_days: number;
  description: string | null;
}

export interface NewsItem {
  ticker: string;
  headline: string | null;
  summary: string | null;
  url: string | null;
  source: string | null;
  published_at: string | null;
}

export interface PricePoint {
  date: string;
  close: number | null;
  sma_200: number | null;
}

export interface IndicatorValue {
  key: string;
  value: number | null;
  description: string | null;
}

export interface Fundamentals {
  date: string;
  pe_ratio: number | null;
  eps: number | null;
  debt_to_equity: number | null;
  dividend_yield: number | null;
  market_cap: number | null;
}

export interface EvaluationCriterion {
  name: string;
  metric: string;
  operator: string;
  threshold_value: number | null;
  threshold_value_max: number | null;
  weight: number;
  direction: Direction;
  observed_value: number | null;
  passed: boolean | null;
  contribution: number;
}

export interface StockDetail {
  stock: Stock;
  last_price: number | null;
  price_change_pct: number | null;
  price_history: PricePoint[];
  indicators: IndicatorValue[];
  fundamentals: Fundamentals | null;
  latest_evaluation: EvaluationSummary | null;
  strategy_name: string | null;
  criteria: EvaluationCriterion[];
}

export interface StrategySignal {
  stock: Stock;
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  buy_score: number;
  sell_score: number;
  run_at: string;
  last_price: number | null;
  price_change_pct: number | null;
}

export interface AnalystSummary {
  summary: string | null;
  generated_at: string | null;
}

export interface AnalystPrompt {
  prompt: string;
  is_default: boolean;
}

// "Perguntar ao Benjamin" (POST /analyst/ask) - histórico mantido só no
// frontend (sem tabela na BD), reenviado a cada pergunta - ver AnalystAskIn
// em app/schemas/common.py (máximo 20 mensagens, aplicado em client.ts).
export interface AnalystChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AnalystAskResponse {
  answer: string;
}

export interface StrategySignalGroup {
  strategy_id: string;
  strategy_name: string;
  horizon: Horizon | null;
  signals: StrategySignal[];
}

export interface OptimizeItem {
  name: string;
  metric: string;
  operator: string;
  threshold_value: number | null;
  threshold_value_max: number | null;
  weight: number;
  direction: Direction;
}

export interface OptimizeResult {
  items: OptimizeItem[];
  backtest_return_pct: number;
  buy_and_hold_return_pct: number | null;
  stocks_evaluated: number;
}

// Campos numéricos vêm como Decimal do backend -> string em JSON (ver
// PriceChange.tsx) - por isso number | string aqui, convertidos com Number()
// no componente que os usa.
export interface Position {
  id: string;
  stock: Stock;
  quantity: number | string;
  avg_cost: number | string;
  cost_total: number | string;
  last_price: number | string | null;
  price_change_pct: number | string | null;
  market_value: number | string | null;
  unrealized_pl: number | string | null;
  unrealized_pl_pct: number | string | null;
  updated_at: string;
}
