/**
 * Main App component with routing.
 *
 * Routes:
 * - / (list view)
 * - /backtest/:id (detail view)
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { BacktestListScreen } from './screens/BacktestList';
import { BacktestDetailScreen } from './screens/BacktestDetail';
import './App.css';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<BacktestListScreen />} />
        <Route path="/backtest/:backtestId" element={<BacktestDetailScreen />} />
      </Routes>
    </BrowserRouter>
  );
}
