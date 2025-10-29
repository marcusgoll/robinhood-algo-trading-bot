/**
 * Backtest detail screen.
 *
 * Displays complete backtest analysis:
 * - Performance metrics table
 * - Four charts (equity, drawdown, win/loss, R-multiple)
 * - Trades table with sorting
 * - Loading and error states
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getBacktestDetail } from '../services/backtestApi';
import type { BacktestDetail } from '../types/backtest';
import { EquityCurveChart } from '../components/EquityCurveChart';
import { DrawdownChart } from '../components/DrawdownChart';
import { WinLossChart } from '../components/WinLossChart';
import { RMultipleChart } from '../components/RMultipleChart';
import { MetricsTable } from '../components/MetricsTable';
import { TradesTable } from '../components/TradesTable';

export function BacktestDetailScreen() {
  const { backtestId } = useParams<{ backtestId: string }>();
  const [data, setData] = useState<BacktestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!backtestId) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getBacktestDetail(backtestId);
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load backtest');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [backtestId]);

  if (loading) {
    return (
      <div className="screen-container">
        <div className="loading">Loading backtest...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="screen-container">
        <div className="error">
          <h2>Error</h2>
          <p>{error}</p>
          <Link to="/" className="back-link">
            ← Back to list
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="screen-container">
        <div className="error">Backtest not found</div>
      </div>
    );
  }

  return (
    <div className="screen-container">
      <header className="screen-header">
        <Link to="/" className="back-link">
          ← Back to list
        </Link>
        <h1>{data.config.strategy}</h1>
        <div className="subtitle">
          {data.config.symbols.join(', ')} | {data.config.start_date} to {data.config.end_date}
        </div>
      </header>

      {data.data_warnings.length > 0 && (
        <div className="warnings">
          <h4>Data Warnings</h4>
          <ul>
            {data.data_warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <section className="metrics-section">
        <MetricsTable metrics={data.metrics} />
      </section>

      <section className="charts-section">
        <div className="charts-grid">
          <EquityCurveChart
            data={data.equity_curve}
            initialCapital={data.config.initial_capital}
          />
          <DrawdownChart data={data.equity_curve} />
          <WinLossChart trades={data.trades} />
          <RMultipleChart trades={data.trades} />
        </div>
      </section>

      <section className="trades-section">
        <TradesTable trades={data.trades} />
      </section>
    </div>
  );
}
