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

export interface StrategyTemplate {
  id: string;
  name: string;
  description: string | null;
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
