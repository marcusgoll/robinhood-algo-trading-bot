/**
 * TypeScript type definitions for backtest API responses.
 *
 * These mirror the Pydantic schemas from api/app/schemas/backtest.py
 */

export interface BacktestSummary {
  id: string;
  strategy: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  total_return: number;
  win_rate: number;
  total_trades: number;
  created_at: string;
}

export interface BacktestListResponse {
  data: BacktestSummary[];
  total: number;
}

export interface TradeDetail {
  symbol: string;
  entry_date: string;
  entry_price: number;
  exit_date: string;
  exit_price: number;
  shares: number;
  pnl: number;
  pnl_pct: number;
  duration_days: number;
  exit_reason: string;
  commission: number;
  slippage: number;
}

export interface PerformanceMetrics {
  total_return: number;
  annualized_return: number;
  cagr: number;
  win_rate: number;
  profit_factor: number;
  average_win: number;
  average_loss: number;
  max_drawdown: number;
  max_drawdown_duration_days: number;
  sharpe_ratio: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
}

export interface EquityCurvePoint {
  timestamp: string;
  equity: number;
}

export interface BacktestConfig {
  strategy: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission: number;
  slippage_pct: number;
}

export interface BacktestDetail {
  config: BacktestConfig;
  metrics: PerformanceMetrics;
  trades: TradeDetail[];
  equity_curve: EquityCurvePoint[];
  data_warnings: string[];
}
