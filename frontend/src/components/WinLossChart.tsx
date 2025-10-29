/**
 * Win/Loss distribution chart component.
 *
 * Visualizes trade profit/loss distribution:
 * - Bar chart showing individual trade P&L
 * - Green bars for wins, red for losses
 * - Sorted by P&L magnitude
 */

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { TradeDetail } from '../types/backtest';

interface WinLossChartProps {
  trades: TradeDetail[];
}

export function WinLossChart({ trades }: WinLossChartProps) {
  // Sort trades by P&L (descending) and map to chart data
  const chartData = [...trades]
    .sort((a, b) => b.pnl - a.pnl)
    .map((trade, index) => ({
      index: index + 1,
      pnl: trade.pnl,
      symbol: trade.symbol,
    }));

  return (
    <div className="chart-container">
      <h3>Win/Loss Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="index"
            tick={{ fontSize: 12 }}
            label={{ value: 'Trade Number (sorted)', position: 'insideBottom', offset: -5, fontSize: 12 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />
          <Tooltip
            formatter={(value: number) => [`$${value.toFixed(2)}`, 'P&L']}
            labelFormatter={(label) => `Trade #${label}`}
          />
          <Bar dataKey="pnl" animationDuration={500}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#22c55e' : '#ef4444'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
