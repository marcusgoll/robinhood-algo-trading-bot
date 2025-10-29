/**
 * Backtest list screen.
 *
 * Displays all backtests with:
 * - Strategy filter dropdown
 * - Date range filters
 * - Summary cards with key metrics
 * - Click to navigate to detail view
 * - Loading and error states
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listBacktests, getStrategies } from '../services/backtestApi';
import type { BacktestSummary } from '../types/backtest';

export function BacktestListScreen() {
  const [backtests, setBacktests] = useState<BacktestSummary[]>([]);
  const [strategies, setStrategies] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const strats = await getStrategies();
        setStrategies(strats);
      } catch (err) {
        console.error('Failed to load strategies:', err);
      }
    };

    fetchStrategies();
  }, []);

  useEffect(() => {
    const fetchBacktests = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await listBacktests({
          strategy: selectedStrategy || undefined,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        });
        setBacktests(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load backtests');
      } finally {
        setLoading(false);
      }
    };

    fetchBacktests();
  }, [selectedStrategy, startDate, endDate]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="screen-container">
      <header className="screen-header">
        <h1>Backtest Results</h1>
      </header>

      <section className="filters">
        <div className="filter-group">
          <label htmlFor="strategy-filter">Strategy</label>
          <select
            id="strategy-filter"
            value={selectedStrategy}
            onChange={(e) => setSelectedStrategy(e.target.value)}
          >
            <option value="">All Strategies</option>
            {strategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="start-date-filter">Start Date</label>
          <input
            type="date"
            id="start-date-filter"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="end-date-filter">End Date</label>
          <input
            type="date"
            id="end-date-filter"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        {(selectedStrategy || startDate || endDate) && (
          <button
            className="clear-filters"
            onClick={() => {
              setSelectedStrategy('');
              setStartDate('');
              setEndDate('');
            }}
          >
            Clear Filters
          </button>
        )}
      </section>

      {loading && (
        <div className="loading">Loading backtests...</div>
      )}

      {error && (
        <div className="error">
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <section className="backtest-grid">
          {backtests.length === 0 ? (
            <div className="no-results">
              No backtests found. Try adjusting your filters.
            </div>
          ) : (
            backtests.map((backtest) => (
              <Link
                key={backtest.id}
                to={`/backtest/${backtest.id}`}
                className="backtest-card"
              >
                <div className="card-header">
                  <h3>{backtest.strategy}</h3>
                  <div className="symbols">{backtest.symbols.join(', ')}</div>
                </div>

                <div className="card-metrics">
                  <div className="metric">
                    <span className="label">Total Return</span>
                    <span className={`value ${backtest.total_return >= 0 ? 'positive' : 'negative'}`}>
                      {backtest.total_return.toFixed(2)}%
                    </span>
                  </div>

                  <div className="metric">
                    <span className="label">Win Rate</span>
                    <span className="value">
                      {(backtest.win_rate * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="metric">
                    <span className="label">Total Trades</span>
                    <span className="value">{backtest.total_trades}</span>
                  </div>
                </div>

                <div className="card-footer">
                  <div className="date-range">
                    {formatDate(backtest.start_date)} — {formatDate(backtest.end_date)}
                  </div>
                  <div className="created-at">
                    Completed {formatDate(backtest.created_at)}
                  </div>
                </div>
              </Link>
            ))
          )}
        </section>
      )}
    </div>
  );
}
