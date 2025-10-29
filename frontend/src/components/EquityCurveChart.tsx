/**
 * Equity curve chart component.
 *
 * Visualizes portfolio value over time with:
 * - Line chart showing equity progression
 * - Green/red fill based on profit/loss
 * - Responsive sizing
 */

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { EquityCurvePoint } from '../types/backtest';

interface EquityCurveChartProps {
  data: EquityCurvePoint[];
  initialCapital: number;
}

export function EquityCurveChart({ data, initialCapital }: EquityCurveChartProps) {
  const isProfit = data.length > 0 && data[data.length - 1].equity >= initialCapital;

  return (
    <div className="chart-container">
      <h3>Equity Curve</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value: number) => [`$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Equity']}
            labelFormatter={(label) => new Date(label).toLocaleDateString('en-US')}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke={isProfit ? '#22c55e' : '#ef4444'}
            strokeWidth={2}
            dot={false}
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
