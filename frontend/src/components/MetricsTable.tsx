/**
 * Performance metrics table component.
 *
 * Displays key performance indicators in grid layout:
 * - Total return, CAGR, Sharpe ratio
 * - Win rate, profit factor
 * - Max drawdown, trade counts
 */

import type { PerformanceMetrics } from '../types/backtest';

interface MetricsTableProps {
  metrics: PerformanceMetrics;
}

interface MetricItem {
  label: string;
  value: string | number;
  highlight?: boolean;
}

export function MetricsTable({ metrics }: MetricsTableProps) {
  const metricItems: MetricItem[] = [
    {
      label: 'Total Return',
      value: `${metrics.total_return.toFixed(2)}%`,
      highlight: true,
    },
    {
      label: 'Annualized Return',
      value: `${metrics.annualized_return.toFixed(2)}%`,
    },
    {
      label: 'CAGR',
      value: `${metrics.cagr.toFixed(2)}%`,
    },
    {
      label: 'Win Rate',
      value: `${(metrics.win_rate * 100).toFixed(1)}%`,
      highlight: true,
    },
    {
      label: 'Profit Factor',
      value: metrics.profit_factor.toFixed(2),
    },
    {
      label: 'Sharpe Ratio',
      value: metrics.sharpe_ratio.toFixed(2),
      highlight: true,
    },
    {
      label: 'Max Drawdown',
      value: `${metrics.max_drawdown.toFixed(2)}%`,
      highlight: true,
    },
    {
      label: 'Max DD Duration',
      value: `${metrics.max_drawdown_duration_days} days`,
    },
    {
      label: 'Total Trades',
      value: metrics.total_trades,
    },
    {
      label: 'Winning Trades',
      value: metrics.winning_trades,
    },
    {
      label: 'Losing Trades',
      value: metrics.losing_trades,
    },
    {
      label: 'Average Win',
      value: `$${metrics.average_win.toFixed(2)}`,
    },
    {
      label: 'Average Loss',
      value: `$${metrics.average_loss.toFixed(2)}`,
    },
  ];

  return (
    <div className="metrics-table">
      <h3>Performance Metrics</h3>
      <div className="metrics-grid">
        {metricItems.map((item) => (
          <div
            key={item.label}
            className={`metric-item ${item.highlight ? 'highlight' : ''}`}
          >
            <div className="metric-label">{item.label}</div>
            <div className="metric-value">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
