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
  latest_evaluation: EvaluationSummary | null;
}

export type Direction = 'buy_signal' | 'sell_signal';

export interface ChecklistItem {
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

export interface ChecklistItemInput {
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

export interface ChecklistTemplate {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  items: ChecklistItem[];
}

export interface EvaluationDetail {
  checklist_item_id: string;
  observed_value: number | null;
  passed: boolean | null;
  contribution: number;
}

export interface Evaluation extends EvaluationSummary {
  stock_id: string;
  checklist_template_id: string;
  details: EvaluationDetail[];
}

export interface MetricInfo {
  key: string;
  kind: 'price' | 'fundamental';
  lookback_days: number;
}
