/**
 * Trades table component.
 *
 * Displays all trades with:
 * - Sortable columns (entry date, symbol, P&L)
 * - Color-coded P&L (green/red)
 * - Pagination (20 trades per page)
 * - Responsive layout
 */

import { useState } from 'react';
import type { TradeDetail } from '../types/backtest';

interface TradesTableProps {
  trades: TradeDetail[];
}

type SortField = 'entry_date' | 'symbol' | 'pnl' | 'pnl_pct' | 'duration_days';
type SortDirection = 'asc' | 'desc';

const TRADES_PER_PAGE = 20;

export function TradesTable({ trades }: TradesTableProps) {
  const [sortField, setSortField] = useState<SortField>('entry_date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [currentPage, setCurrentPage] = useState(1);

  // Sort trades
  const sortedTrades = [...trades].sort((a, b) => {
    let aValue: string | number;
    let bValue: string | number;

    if (sortField === 'entry_date') {
      aValue = new Date(a.entry_date).getTime();
      bValue = new Date(b.entry_date).getTime();
    } else {
      aValue = a[sortField];
      bValue = b[sortField];
    }

    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  // Paginate
  const totalPages = Math.ceil(sortedTrades.length / TRADES_PER_PAGE);
  const startIndex = (currentPage - 1) * TRADES_PER_PAGE;
  const paginatedTrades = sortedTrades.slice(startIndex, startIndex + TRADES_PER_PAGE);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="trades-table">
      <h3>All Trades ({trades.length})</h3>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th onClick={() => handleSort('symbol')} className="sortable">
                Symbol {sortField === 'symbol' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('entry_date')} className="sortable">
                Entry Date {sortField === 'entry_date' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Exit Date</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Shares</th>
              <th onClick={() => handleSort('pnl')} className="sortable">
                P&L {sortField === 'pnl' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('pnl_pct')} className="sortable">
                P&L % {sortField === 'pnl_pct' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('duration_days')} className="sortable">
                Duration {sortField === 'duration_days' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Exit Reason</th>
            </tr>
          </thead>
          <tbody>
            {paginatedTrades.map((trade, index) => (
              <tr key={`${trade.symbol}-${trade.entry_date}-${index}`}>
                <td className="symbol">{trade.symbol}</td>
                <td>{formatDate(trade.entry_date)}</td>
                <td>{formatDate(trade.exit_date)}</td>
                <td>${trade.entry_price.toFixed(2)}</td>
                <td>${trade.exit_price.toFixed(2)}</td>
                <td>{trade.shares}</td>
                <td className={trade.pnl >= 0 ? 'positive' : 'negative'}>
                  ${trade.pnl.toFixed(2)}
                </td>
                <td className={trade.pnl_pct >= 0 ? 'positive' : 'negative'}>
                  {trade.pnl_pct.toFixed(2)}%
                </td>
                <td>{trade.duration_days}d</td>
                <td className="exit-reason">{trade.exit_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </button>
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
