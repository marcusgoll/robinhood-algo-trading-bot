"""
Strategy Comparison Example

Compares multiple strategies against the same historical data to identify
the best-performing approach. This example demonstrates:
- Running multiple backtests programmatically
- Comparing performance metrics across strategies
- Ranking strategies by risk-adjusted returns

Run:
    python examples/strategy_comparison.py
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any

from src.trading_bot.backtest.engine import BacktestEngine
from src.trading_bot.backtest.models import BacktestConfig, BacktestResult
from src.trading_bot.backtest.historical_data_manager import HistoricalDataManager
from src.trading_bot.backtest.performance_calculator import PerformanceCalculator
from examples.sample_strategies import BuyAndHoldStrategy, MomentumStrategy


def run_backtest(strategy, strategy_name: str, historical_data: list, config: BacktestConfig) -> Dict[str, Any]:
    """
    Run a single backtest and return results.

    Args:
        strategy: Strategy instance to backtest
        strategy_name: Human-readable strategy name
        historical_data: Historical price data
        config: Backtest configuration

    Returns:
        Dictionary with strategy name, result, and metrics
    """
    print(f"  Running {strategy_name}...")
    engine = BacktestEngine(config)
    result = engine.run(strategy, historical_data)

    calculator = PerformanceCalculator()
    metrics = calculator.calculate_metrics(result.trades, result.equity_curve, config)

    return {
        "name": strategy_name,
        "result": result,
        "metrics": metrics,
    }


def print_comparison_table(results: List[Dict[str, Any]]):
    """
    Print formatted comparison table of strategy results.

    Args:
        results: List of backtest results with metrics
    """
    print("\n" + "=" * 120)
    print("STRATEGY COMPARISON")
    print("=" * 120)

    # Table header
    header = (
        f"{'Strategy':<30} {'Return':>10} {'Ann. Ret':>10} {'Sharpe':>8} "
        f"{'Max DD':>10} {'Win Rate':>10} {'Trades':>8}"
    )
    print(header)
    print("-" * 120)

    # Table rows
    for r in results:
        metrics = r["metrics"]
        row = (
            f"{r['name']:<30} "
            f"{metrics.total_return * 100:>9.2f}% "
            f"{metrics.annualized_return * 100:>9.2f}% "
            f"{metrics.sharpe_ratio:>8.2f} "
            f"{metrics.max_drawdown * 100:>9.2f}% "
            f"{metrics.win_rate * 100:>9.1f}% "
            f"{metrics.total_trades:>8}"
        )
        print(row)

    print("=" * 120)


def print_detailed_analysis(results: List[Dict[str, Any]]):
    """
    Print detailed analysis for each strategy.

    Args:
        results: List of backtest results with metrics
    """
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS")
    print("=" * 80)

    for r in results:
        metrics = r["metrics"]
        result = r["result"]

        print(f"\n{r['name']}")
        print("-" * 80)
        print(f"  Total Return:        {metrics.total_return * 100:>10.2f}%")
        print(f"  Annualized Return:   {metrics.annualized_return * 100:>10.2f}%")
        print(f"  CAGR:                {metrics.cagr * 100:>10.2f}%")
        print(f"  Sharpe Ratio:        {metrics.sharpe_ratio:>10.2f}")
        print(f"  Max Drawdown:        {metrics.max_drawdown * 100:>10.2f}%")
        print(f"  Max DD Duration:     {metrics.max_drawdown_duration_days:>10} days")
        print(f"  Win Rate:            {metrics.win_rate * 100:>10.1f}%")
        print(f"  Profit Factor:       {metrics.profit_factor:>10.2f}")
        print(f"  Average Win:         ${metrics.average_win:>10.2f}")
        print(f"  Average Loss:        ${metrics.average_loss:>10.2f}")
        print(f"  Total Trades:        {metrics.total_trades:>10}")
        print(f"  Execution Time:      {result.execution_time_seconds:>10.2f}s")


def rank_strategies(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank strategies by Sharpe ratio (risk-adjusted returns).

    Args:
        results: List of backtest results with metrics

    Returns:
        Sorted list (best to worst by Sharpe ratio)
    """
    return sorted(results, key=lambda r: r["metrics"].sharpe_ratio, reverse=True)


def main():
    """Run strategy comparison backtest."""
    print("=" * 80)
    print("STRATEGY COMPARISON EXAMPLE")
    print("=" * 80)

    # Step 1: Fetch historical data (shared across all strategies)
    print("\n[1/3] Fetching historical data...")
    symbol = "AAPL"
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)

    data_manager = HistoricalDataManager()
    historical_data = data_manager.fetch_data(symbol, start_date, end_date)
    print(f"  Symbol: {symbol}")
    print(f"  Period: {start_date.date()} to {end_date.date()}")
    print(f"  Trading days: {len(historical_data)}")

    # Step 2: Configure backtest
    base_config = BacktestConfig(
        strategy_class=None,  # Will be overridden for each strategy
        symbols=[symbol],
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal("100000"),
        commission=Decimal("0"),
        slippage_pct=Decimal("0.001"),
    )

    # Step 3: Run all strategies
    print("\n[2/3] Running strategies...")
    results = []

    # Strategy 1: Buy and Hold (baseline)
    results.append(run_backtest(
        BuyAndHoldStrategy(),
        "Buy and Hold (Baseline)",
        historical_data,
        base_config,
    ))

    # Strategy 2: Momentum (10/30 day MA)
    results.append(run_backtest(
        MomentumStrategy(short_window=10, long_window=30),
        "Momentum (MA 10/30)",
        historical_data,
        base_config,
    ))

    # Strategy 3: Momentum (20/50 day MA)
    results.append(run_backtest(
        MomentumStrategy(short_window=20, long_window=50),
        "Momentum (MA 20/50)",
        historical_data,
        base_config,
    ))

    # Strategy 4: Momentum (5/20 day MA - fast)
    results.append(run_backtest(
        MomentumStrategy(short_window=5, long_window=20),
        "Momentum (MA 5/20 - Fast)",
        historical_data,
        base_config,
    ))

    # Step 4: Rank and display results
    print("\n[3/3] Analyzing results...")
    ranked_results = rank_strategies(results)

    # Display comparison table
    print_comparison_table(ranked_results)

    # Display detailed analysis
    print_detailed_analysis(ranked_results)

    # Display winner
    print("\n" + "=" * 80)
    print("WINNER (by Sharpe Ratio)")
    print("=" * 80)
    winner = ranked_results[0]
    print(f"Strategy: {winner['name']}")
    print(f"Sharpe Ratio: {winner['metrics'].sharpe_ratio:.2f}")
    print(f"Total Return: {winner['metrics'].total_return * 100:.2f}%")
    print(f"Max Drawdown: {winner['metrics'].max_drawdown * 100:.2f}%")
    print("=" * 80)

    # Insights
    print("\nInsights:")
    print("  - Sharpe ratio measures risk-adjusted returns (higher is better)")
    print("  - Compare strategies on multiple metrics, not just total return")
    print("  - Consider drawdown and win rate for risk assessment")
    print("  - Test strategies across different time periods for robustness")
    print("\nNext steps:")
    print("  1. Try different parameter combinations for each strategy")
    print("  2. Test strategies on different stocks and time periods")
    print("  3. Create your own custom strategy (see custom_strategy_example.py)")


if __name__ == "__main__":
    main()
