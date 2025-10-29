/**
 * Drawdown chart component.
 *
 * Visualizes portfolio drawdown over time:
 * - Area chart showing percentage drawdown from peak
 * - Red fill for negative values
 * - Calculated from equity curve data
 */

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { EquityCurvePoint } from '../types/backtest';

interface DrawdownChartProps {
  data: EquityCurvePoint[];
}

/**
 * Calculate drawdown percentage at each point.
 */
function calculateDrawdown(equityCurve: EquityCurvePoint[]) {
  let peak = 0;
  return equityCurve.map((point) => {
    if (point.equity > peak) {
      peak = point.equity;
    }
    const drawdown = peak > 0 ? ((point.equity - peak) / peak) * 100 : 0;
    return {
      timestamp: point.timestamp,
      drawdown,
    };
  });
}

export function DrawdownChart({ data }: DrawdownChartProps) {
  const drawdownData = calculateDrawdown(data);

  return (
    <div className="chart-container">
      <h3>Drawdown</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={drawdownData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.2} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => `${value.toFixed(0)}%`}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(2)}%`, 'Drawdown']}
            labelFormatter={(label) => new Date(label).toLocaleDateString('en-US')}
          />
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke="#ef4444"
            fill="url(#drawdownGradient)"
            animationDuration={500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
