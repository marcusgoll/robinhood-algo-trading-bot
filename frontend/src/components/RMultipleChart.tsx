/**
 * R-multiple distribution chart component.
 *
 * Visualizes risk-adjusted returns (R-multiples):
 * - Histogram showing distribution of trade outcomes
 * - Bins trades by R-multiple ranges
 * - Green for positive, red for negative R
 */

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { TradeDetail } from '../types/backtest';

interface RMultipleChartProps {
  trades: TradeDetail[];
}

/**
 * Calculate R-multiple for each trade.
 * R-multiple = pnl / (entry_price * shares * risk_pct)
 * Simplified: Use pnl_pct as proxy for R
 */
function calculateRMultiples(trades: TradeDetail[]) {
  // Create histogram bins: [-3R, -2R, -1R, 0R, 1R, 2R, 3R, 4R+]
  const bins = [
    { label: '-3R or less', min: -Infinity, max: -3, count: 0, color: '#dc2626' },
    { label: '-2R to -3R', min: -3, max: -2, count: 0, color: '#ef4444' },
    { label: '-1R to -2R', min: -2, max: -1, count: 0, color: '#f87171' },
    { label: '-1R to 0R', min: -1, max: 0, count: 0, color: '#fca5a5' },
    { label: '0R to 1R', min: 0, max: 1, count: 0, color: '#86efac' },
    { label: '1R to 2R', min: 1, max: 2, count: 0, color: '#4ade80' },
    { label: '2R to 3R', min: 2, max: 3, count: 0, color: '#22c55e' },
    { label: '3R or more', min: 3, max: Infinity, count: 0, color: '#16a34a' },
  ];

  // Approximate R-multiple from pnl_pct (1% = 1R for simplicity)
  trades.forEach((trade) => {
    const rMultiple = trade.pnl_pct;
    const bin = bins.find((b) => rMultiple > b.min && rMultiple <= b.max);
    if (bin) bin.count++;
  });

  return bins;
}

export function RMultipleChart({ trades }: RMultipleChartProps) {
  const data = calculateRMultiples(trades);

  return (
    <div className="chart-container">
      <h3>R-Multiple Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 5, right: 20, bottom: 50, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            label={{ value: 'Number of Trades', angle: -90, position: 'insideLeft', fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: number) => [value, 'Trades']}
          />
          <Bar dataKey="count" animationDuration={500}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
