# Day Trading System Implementation Plan

**Date**: November 5, 2025
**Project**: Multi-Symbol ML-Driven Day Trading System
**Goal**: Trade whole market with high-frequency entries/exits for maximum returns
**Status**: PLANNING PHASE

---

## Executive Summary

Build an automated day trading system that:
1. **Screens** 5000+ stocks → 20-50 watchlist candidates (liquidity + momentum)
2. **Predicts** short-term price movements (30min-2hr horizon) using ML
3. **Executes** emotion-free entries/exits with strict risk management
4. **Scales** to 5-10 simultaneous positions across diverse sectors

**Expected Performance**:
- Win rate: 55-60% (based on ML research)
- Risk/reward: 2:1 (target +2%, stop -1%)
- Trades/day: 10-20 (high frequency)
- Sharpe ratio target: 2.0+

**Timeline**: 10-14 weeks to production
**Estimated Cost**: $2,000-$5,000 (data subscriptions, infrastructure)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         TRADING SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   SCREENER    │─────>│  ML ENGINE   │─────>│  EXECUTION   │ │
│  │               │      │              │      │              │ │
│  │ • Volume      │      │ • Predict    │      │ • Entry      │ │
│  │ • Volatility  │      │ • Confidence │      │ • Exit       │ │
│  │ • Momentum    │      │ • Ranking    │      │ • Risk Mgmt  │ │
│  │ • Technical   │      │              │      │              │ │
│  └───────────────┘      └──────────────┘      └──────────────┘ │
│        ↓                      ↓                      ↓          │
│  20-50 symbols           Top 5-10 signals      Position sizing  │
│  (refreshed 15min)       (confidence > 65%)    (2:1 R/R)       │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   MONITORING & LOGGING                     │ │
│  │  • Real-time P&L  • Trade history  • Performance metrics  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown

### Phase 7A: Shorter Horizon Validation (Week 1-2)

**Goal**: Validate ML model works for day trading timeframes (30min-2hr)

**Tasks**:
1. Test baseline model with horizons: 10, 20, 30 bars (50min, 1.7hr, 2.5hr)
2. Compare accuracy vs. 78-bar (6.5hr) baseline
3. Measure trade frequency vs. accuracy tradeoff
4. Validate on SPY, QQQ, TSLA

**Deliverables**:
- `validate_short_horizons.py` - Multi-horizon testing script
- `short_horizon_results.csv` - Performance comparison
- Recommendation: Optimal horizon for day trading

**Success Criteria**:
- At least one horizon achieves 55%+ accuracy
- Stable performance (low variance across seeds)

**Timeline**: 1-2 weeks
**Risk**: Shorter horizons may be too noisy (lower accuracy)
**Mitigation**: Test multiple horizons, use ensemble if needed

---

### Phase 7B: Stock Screener Development (Week 3-4)

**Goal**: Build real-time screener to identify trading candidates

**Technical Specifications**:

**Screening Criteria**:
```python
# Primary Filters (Hard Requirements)
volume > 500_000 shares/day        # Liquidity
price >= $10 and price <= $500     # Avoid penny stocks, reasonable capital
average_true_range > 1.5%          # Volatility for profit opportunity

# Secondary Filters (Ranking Criteria)
unusual_volume_ratio > 1.5         # Volume spike (interest)
price_change_percent > 1.0         # Momentum
relative_strength > 50             # Outperforming market
gap_percent > 0.5                  # Morning gap (catalyst)

# Diversity Requirements
max_per_sector = 3                 # Sector diversification
min_market_cap = $1B               # Stability
```

**Data Sources**:
- Alpaca (free tier): Real-time quotes, historical bars
- Upgrade option: Polygon.io ($200/mo) for faster updates

**Refresh Rate**: Every 15-30 minutes (avoid API rate limits)

**Tasks**:
1. Build screening pipeline
   - Fetch universe (Russell 3000 or similar)
   - Apply filters in sequence
   - Rank by momentum + volume
   - Output top 20-50 symbols

2. Caching strategy
   - Cache screener results for 15 minutes
   - Avoid redundant API calls
   - Store historical watchlists for analysis

3. Testing
   - Backtest screener on historical data
   - Verify it identifies known movers (TSLA earnings, NVDA breakouts)
   - Measure false positive rate

**Deliverables**:
- `screener.py` - Core screening logic
- `screener_config.yaml` - Configurable criteria
- `test_screener_historical.py` - Validation script
- `screener_performance_report.md` - Historical hit rate

**Success Criteria**:
- Generates 20-50 symbols per run
- Includes 70%+ of actual day's movers
- Runs in <30 seconds

**Timeline**: 2 weeks
**Risk**: Screener misses best opportunities or includes false signals
**Mitigation**: Backtesting, iterative tuning, multiple criteria

---

### Phase 7C: Multi-Symbol ML Inference (Week 5-6)

**Goal**: Scale ML predictions to entire watchlist in real-time

**Technical Specifications**:

**Model Serving**:
```python
class TradingMLEngine:
    def __init__(self, model_path):
        self.model = load_pretrained_model(model_path)
        self.scaler = load_scaler()

    def predict_batch(self, symbols: List[str]) -> List[Prediction]:
        """
        Run predictions on multiple symbols in parallel.

        Returns:
            List of predictions with confidence scores
        """
        # Fetch 5Min bars for all symbols (last 100 bars)
        data = fetch_multi_symbol_data(symbols, bars=100)

        # Extract features (parallel processing)
        features = extract_features_parallel(data)

        # Batch inference (GPU if available)
        predictions = self.model.predict(features)

        # Calculate confidence scores
        confidences = calculate_confidence(predictions, features)

        return [
            Prediction(
                symbol=sym,
                direction='LONG' if pred > 0 else 'SHORT',
                confidence=conf,
                expected_return=pred
            )
            for sym, pred, conf in zip(symbols, predictions, confidences)
        ]
```

**Confidence Scoring**:
- **High confidence (>80%)**: Model strongly agrees on direction
  - Use larger position size (2-3% of portfolio)
  - Tighter stops (0.75%)

- **Medium confidence (65-80%)**: Standard signal
  - Normal position size (1-2% of portfolio)
  - Standard stops (1%)

- **Low confidence (<65%)**: Skip trade
  - Accuracy likely <55%, not worth risk

**Performance Requirements**:
- Process 50 symbols in <10 seconds
- Cache feature calculations (update every 5 minutes)
- Parallel execution (use all CPU cores)

**Tasks**:
1. Model serving infrastructure
   - Load model once at startup
   - Keep in memory for fast inference
   - Batch predictions for efficiency

2. Confidence calibration
   - Backtest confidence scores vs. actual outcomes
   - Tune threshold (may need 70% instead of 65%)
   - Separate models per symbol type (ETF vs. individual stock)

3. Real-time data pipeline
   - WebSocket connection to Alpaca
   - 5Min bar aggregation
   - Feature calculation on-the-fly

**Deliverables**:
- `ml_engine.py` - Model serving + inference
- `confidence_calibration.py` - Score tuning
- `realtime_pipeline.py` - Data ingestion
- `ml_engine_benchmark.md` - Performance metrics

**Success Criteria**:
- 50 symbols processed in <10 seconds
- Confidence scores correlate with actual win rate
- Uptime: 99%+ during market hours

**Timeline**: 2 weeks
**Risk**: Inference too slow, confidence miscalibrated
**Mitigation**: GPU acceleration, pre-computed features, iterative calibration

---

### Phase 7D: Execution & Risk Management (Week 7-8)

**Goal**: Implement emotion-free entry/exit with strict risk controls

**Position Sizing**:
```python
def calculate_position_size(
    account_balance: float,
    confidence: float,
    stock_price: float,
    volatility: float
) -> int:
    """
    Kelly Criterion adjusted for confidence and volatility.
    """
    # Base risk per trade: 1-2% of account
    risk_per_trade = account_balance * 0.01

    # Adjust for confidence (higher confidence = larger position)
    confidence_multiplier = confidence / 0.70  # Scale around 70% baseline

    # Adjust for volatility (higher volatility = smaller position)
    volatility_divisor = max(volatility / 0.02, 1.0)  # Normalize around 2% ATR

    # Calculate shares
    position_value = risk_per_trade * confidence_multiplier / volatility_divisor
    shares = int(position_value / stock_price)

    # Caps
    max_position_value = account_balance * 0.20  # Never more than 20% in one stock
    shares = min(shares, int(max_position_value / stock_price))

    return shares
```

**Entry Rules**:
- **Confidence threshold**: >65% (configurable)
- **Maximum positions**: 5-10 simultaneous trades
- **Sector limit**: Max 3 positions per sector
- **Timing**: Only enter 9:45am-3:30pm ET (avoid open/close volatility)
- **Order type**: Limit orders (avoid slippage on low liquidity)

**Exit Rules**:
```python
class TradeManager:
    def monitor_position(self, position):
        """Check exit conditions every minute."""

        current_pnl_pct = (position.current_price - position.entry_price) / position.entry_price
        time_in_position = now() - position.entry_time

        # Take profit (target: +1.5% to +3% depending on volatility)
        if current_pnl_pct >= position.take_profit_pct:
            return 'EXIT_PROFIT'

        # Stop loss (risk: -0.75% to -1.5%)
        if current_pnl_pct <= -position.stop_loss_pct:
            return 'EXIT_STOP'

        # Time-based exit (no movement after 2 hours)
        if time_in_position > timedelta(hours=2) and abs(current_pnl_pct) < 0.005:
            return 'EXIT_TIMEOUT'

        # Market close (always exit 3:55pm)
        if now().time() >= time(15, 55):
            return 'EXIT_EOD'

        return 'HOLD'
```

**Risk Controls**:
- **Daily loss limit**: -3% of account (stop trading for the day)
- **Weekly loss limit**: -5% of account (stop trading for the week)
- **Max drawdown**: -10% (pause and review strategy)
- **Position limits**: Never >20% in single stock, >50% total deployed

**Tasks**:
1. Order execution system
   - Place orders via Alpaca API
   - Handle partial fills, rejections
   - Retry logic for failed orders

2. Position monitoring
   - Check exit conditions every minute
   - Automated stop-loss execution
   - Profit-taking logic

3. Risk management dashboard
   - Real-time P&L tracking
   - Position exposure by sector
   - Daily/weekly performance

**Deliverables**:
- `execution_engine.py` - Order placement + monitoring
- `risk_manager.py` - Position sizing + limits
- `dashboard.py` - Real-time monitoring UI
- `risk_management_rules.md` - Full rule documentation

**Success Criteria**:
- Orders execute within 5 seconds of signal
- Stop-losses never missed (100% execution)
- Risk limits enforced automatically

**Timeline**: 2 weeks
**Risk**: Slippage, failed orders, risk limits violated
**Mitigation**: Extensive testing, conservative limits, kill switch

---

### Phase 7E: Backtesting Framework (Week 9-10)

**Goal**: Validate entire system on historical data before risking capital

**Simulation Specifications**:

**Data Requirements**:
- 6 months of historical 5Min bars
- All symbols from historical screener runs
- Realistic transaction costs

**Transaction Costs**:
```python
# Per-trade costs
commission = 0  # Alpaca commission-free
slippage = stock_price * 0.001  # 0.1% slippage (market orders)
sec_fee = trade_value * 0.0000221  # SEC fee
finra_taf = shares * 0.000145  # FINRA TAF (capped)

# Total cost per round-trip
total_cost_pct = (slippage * 2 + sec_fee + finra_taf) / trade_value
# Typically: 0.2-0.3% per round-trip
```

**Metrics to Track**:
```python
class BacktestResults:
    # Performance
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float

    # Trade statistics
    total_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float  # gross_profit / gross_loss

    # Risk metrics
    average_position_duration: timedelta
    largest_loss: float
    consecutive_losses: int

    # Execution
    average_slippage: float
    order_fill_rate: float
```

**Testing Scenarios**:
1. **Bull market** (Jan-Mar 2024): Does system capture upside?
2. **Bear market** (Aug-Oct 2024): Does risk management protect?
3. **Sideways market** (Apr-Jun 2024): Do we avoid overtrading?
4. **High volatility** (Feb 2024 correction): Do stop-losses work?

**Tasks**:
1. Build backtesting engine
   - Replay historical bars
   - Simulate screener, predictions, executions
   - Account for realistic constraints (data lag, order delays)

2. Parameter sensitivity testing
   - Test different confidence thresholds (60%, 65%, 70%)
   - Test different stop-loss levels (0.75%, 1%, 1.5%)
   - Test different position sizing rules

3. Walk-forward optimization
   - Train on 4 months, test on 1 month
   - Roll forward monthly
   - Measure performance degradation over time

**Deliverables**:
- `backtester.py` - Full system simulation
- `backtest_results/` - Results for each scenario
- `BACKTESTING_REPORT.md` - Comprehensive analysis
- `optimal_parameters.yaml` - Tuned configuration

**Success Criteria**:
- Sharpe ratio > 2.0 across all scenarios
- Max drawdown < 15%
- Profit factor > 1.5 (win more than you lose)
- Consistent performance across market regimes

**Timeline**: 2 weeks
**Risk**: Overfitting to historical data, unrealistic assumptions
**Mitigation**: Multiple scenarios, conservative estimates, walk-forward validation

---

### Phase 7F: Paper Trading (Week 11-14)

**Goal**: Live validation without risking capital

**Setup**:
- Alpaca paper trading account ($100k virtual capital)
- Full system running in production mode
- Real-time execution, no simulation

**Monitoring**:
- Daily performance review
- Compare actual vs. backtested results
- Track unexpected behaviors

**Tasks**:
1. Deploy to production environment
   - Cloud server (AWS/GCP) or local machine
   - Persistent database for trade history
   - Monitoring + alerting

2. Run for 4-6 weeks
   - Minimum 100 trades for statistical significance
   - Track all metrics from backtesting
   - Document issues and fixes

3. Iteration
   - Tune parameters based on live results
   - Fix bugs discovered in production
   - Add missing features

**Success Criteria**:
- Win rate within 5% of backtested (e.g., 55-60% if backtested 57%)
- Sharpe ratio within 20% of backtested
- No catastrophic failures (system crashes, order errors)
- Profit factor > 1.3

**Timeline**: 4-6 weeks
**Risk**: Paper trading differs from live (no slippage, unlimited liquidity)
**Mitigation**: Conservative live deployment, start with small capital

---

## Technology Stack

### Data & APIs
- **Market data**: Alpaca (free tier initially, upgrade to Polygon.io if needed)
- **Execution**: Alpaca Trading API
- **Alternative**: Interactive Brokers (lower latency, more expensive)

### Backend
- **Language**: Python 3.11+
- **ML framework**: PyTorch (existing models)
- **Data processing**: Pandas, NumPy
- **Async operations**: asyncio for parallel execution
- **Database**: PostgreSQL (trade history, positions)
- **Cache**: Redis (real-time quotes, feature cache)

### Infrastructure
- **Hosting**: AWS EC2 or local dedicated machine
- **OS**: Ubuntu 22.04 LTS
- **Monitoring**: Grafana + Prometheus
- **Logging**: ELK stack (Elasticsearch, Logstash, Kibana)
- **Alerting**: Slack/Discord webhooks

### Development Tools
- **Version control**: Git
- **CI/CD**: GitHub Actions
- **Testing**: pytest
- **Documentation**: Markdown + Jupyter notebooks

---

## Resource Requirements

### Time Commitment
- **Development**: 40-60 hours/week for 10-14 weeks
- **Monitoring (live)**: 2-4 hours/day during market hours
- **Maintenance**: 5-10 hours/week ongoing

### Capital Requirements

**Initial Setup**:
- Data subscriptions: $0-$200/month (Polygon.io optional)
- Cloud hosting: $50-$200/month (EC2 t3.medium or similar)
- Development tools: $0 (open source)
- **Total**: $50-$400/month

**Trading Capital**:
- Minimum: $25,000 (pattern day trader requirement)
- Recommended: $50,000-$100,000 (proper diversification)

**Risk Budget**:
- Maximum loss tolerance: -10% ($5k-$10k)
- Expected monthly return: 5-10% ($2.5k-$10k)

### Skill Requirements
- Python programming (intermediate-advanced)
- ML/statistics fundamentals
- Trading knowledge (technical analysis, risk management)
- System administration (servers, databases)

---

## Risk Assessment

### Technical Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| ML model degradation over time | High | Medium | Monthly retraining, walk-forward validation |
| API downtime (Alpaca) | High | Low | Backup data source (Polygon), local caching |
| System crash during trading hours | Critical | Low | Auto-restart, health checks, kill switch |
| Data pipeline lag | Medium | Medium | Latency monitoring, timeout alerts |
| Order execution failures | High | Low | Retry logic, manual override capability |

### Market Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Flash crash (circuit breakers) | High | Very Low | Stop trading on market halt, max position limits |
| Correlation breakdown | Medium | Medium | Sector diversification, position limits |
| Slippage exceeds estimates | Medium | Medium | Use limit orders, avoid low liquidity stocks |
| Model stops working (regime change) | High | Medium | Performance monitoring, pause if win rate <50% |
| Pattern day trader violation | Critical | Low | Track day trades, warn at 3/5 limit |

### Financial Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Rapid capital loss | Critical | Low | Daily/weekly loss limits, kill switch |
| Death by a thousand cuts (fees) | Medium | Medium | Model transaction costs, reduce trade frequency if needed |
| Opportunity cost vs. index | Low | Medium | Track vs. SPY benchmark, adjust if underperforming |

---

## Success Metrics

### Phase Success Criteria

| Phase | Metric | Target |
|-------|--------|--------|
| 7A (Short Horizons) | Accuracy | >55% |
| 7B (Screener) | Hit rate | >70% of day's movers |
| 7C (ML Engine) | Inference speed | <10s for 50 symbols |
| 7D (Execution) | Order fill rate | >98% |
| 7E (Backtesting) | Sharpe ratio | >2.0 |
| 7F (Paper Trading) | Win rate | 55-60% |

### Production Success Criteria (3 months)

**Minimum Viable Performance**:
- Monthly return: >3% (covers transaction costs + small profit)
- Sharpe ratio: >1.5
- Max drawdown: <10%
- Win rate: >52%

**Target Performance**:
- Monthly return: 5-10%
- Sharpe ratio: >2.0
- Max drawdown: <7%
- Win rate: 55-60%

**Excellence Performance**:
- Monthly return: >12%
- Sharpe ratio: >2.5
- Max drawdown: <5%
- Win rate: >60%

---

## Fallback Strategies

### If Short Horizons Don't Work (Phase 7A)
- **Plan B**: Stick with longer horizons (78 bars / 6.5 hours)
- **Impact**: Fewer trades per day (3-5 instead of 10-20), lower frequency
- **Adjustment**: Adjust position sizing, longer holds

### If Screener Has Low Hit Rate (Phase 7B)
- **Plan B**: Use fixed watchlist (top 50 liquid stocks by volume)
- **Impact**: Miss some opportunities, but consistent universe
- **Adjustment**: Focus on blue-chip stocks (AAPL, MSFT, NVDA, TSLA, SPY, QQQ)

### If Backtesting Shows Poor Performance (Phase 7E)
- **Plan B**: Hybrid approach - ML for direction + technical indicators for entry timing
- **Impact**: More complex, but potentially more robust
- **Adjustment**: Add MACD, RSI divergences, support/resistance levels

### If Paper Trading Fails (Phase 7F)
- **Plan B**: Return to research phase, test different architectures (Transformer, GRU)
- **Impact**: 4-8 weeks additional research time
- **Adjustment**: May need more advanced ML techniques or different data sources

---

## Cost-Benefit Analysis

### Investment
- **Time**: 400-800 hours (10-14 weeks × 40-60 hrs/week)
- **Money**: $500-$2,000 (setup costs for 4 months)
- **Capital at risk**: $5,000-$10,000 (10% of $50k-$100k account)

### Expected Returns (Conservative Estimate)

**Year 1**:
- Starting capital: $50,000
- Target return: 5% monthly × 8 months (after 4-month development)
- Expected P&L: $50k × (1.05^8 - 1) = **$23,872 profit**
- ROI: 47.7%

**Breakeven Analysis**:
- Need 2-3 months of profitable trading to cover development costs
- If achieve 5% monthly, break even by Month 3

**Downside Risk**:
- Worst case: -10% max drawdown = -$5,000
- Lost time opportunity cost: ~$40k-$80k (if could work elsewhere)

---

## Next Steps

### Immediate Actions (This Week)

1. **Validate short horizons** (Option A from earlier)
   - Run `validate_short_horizons.py` on SPY
   - Test 10, 20, 30 bar predictions
   - Confirm >55% accuracy at shorter timeframes

2. **Review existing trading bot code**
   - Check if any screener logic exists
   - Identify reusable components
   - Document gaps

3. **Set up development environment**
   - Ensure Alpaca API credentials valid
   - Install any missing dependencies
   - Create project structure

### Decision Points

**After Phase 7A (Week 2)**:
- GO: If accuracy >55% at any short horizon → Proceed to 7B
- NO-GO: If all horizons <52% → Return to research, try different architectures

**After Phase 7E (Week 10)**:
- GO: If Sharpe >1.5, max DD <15% → Proceed to paper trading
- PAUSE: If Sharpe <1.0 → Re-tune parameters, extend backtesting
- NO-GO: If consistent losses → Fundamental approach change needed

**After Phase 7F (Week 14)**:
- GO LIVE: If paper trading matches backtesting → Start with $10k live
- EXTEND: If close but needs tuning → Additional 2-4 weeks paper trading
- STOP: If paper trading shows <50% win rate → Major redesign needed

---

## Appendix A: Sample Directory Structure

```
trading-system/
├── config/
│   ├── screener_config.yaml
│   ├── ml_config.yaml
│   ├── execution_config.yaml
│   └── risk_config.yaml
├── src/
│   ├── screener/
│   │   ├── filters.py
│   │   ├── ranking.py
│   │   └── watchlist_manager.py
│   ├── ml/
│   │   ├── model.py
│   │   ├── features.py
│   │   ├── inference.py
│   │   └── confidence.py
│   ├── execution/
│   │   ├── order_manager.py
│   │   ├── position_tracker.py
│   │   └── risk_manager.py
│   ├── data/
│   │   ├── alpaca_client.py
│   │   ├── realtime_pipeline.py
│   │   └── cache.py
│   └── backtesting/
│       ├── simulator.py
│       ├── metrics.py
│       └── analysis.py
├── tests/
├── notebooks/
│   ├── phase7a_short_horizons.ipynb
│   ├── phase7b_screener_validation.ipynb
│   └── phase7e_backtest_analysis.ipynb
├── scripts/
│   ├── validate_short_horizons.py
│   ├── run_screener.py
│   ├── backtest.py
│   └── paper_trading.py
├── models/
│   ├── baseline_spy_model.pth
│   └── baseline_spy_scaler.pkl
├── logs/
├── results/
└── docs/
    ├── ARCHITECTURE.md
    ├── RISK_MANAGEMENT.md
    └── OPERATIONS_MANUAL.md
```

---

## Appendix B: Key Code Snippets

### Entry Point Example
```python
# main.py
async def main():
    # Initialize components
    screener = Screener(config.screener)
    ml_engine = MLEngine(config.ml)
    executor = ExecutionEngine(config.execution)
    risk_mgr = RiskManager(config.risk)

    while market_open():
        # 1. Screen for candidates (every 15 minutes)
        if time_to_screen():
            watchlist = screener.scan()
            log.info(f"Watchlist: {len(watchlist)} symbols")

        # 2. Generate ML predictions
        predictions = ml_engine.predict_batch(watchlist)
        signals = [p for p in predictions if p.confidence > 0.65]
        log.info(f"Signals: {len(signals)} high-confidence")

        # 3. Check risk limits and execute
        for signal in signals:
            if risk_mgr.can_open_position(signal):
                position_size = risk_mgr.calculate_size(signal)
                executor.place_order(signal, position_size)

        # 4. Monitor existing positions
        for position in executor.get_open_positions():
            exit_reason = risk_mgr.check_exit(position)
            if exit_reason:
                executor.close_position(position, exit_reason)

        await asyncio.sleep(60)  # Check every minute
```

---

## Appendix C: Monitoring Dashboard Mockup

```
╔════════════════════════════════════════════════════════════════╗
║  TRADING SYSTEM DASHBOARD       2025-11-05 14:23:15 EST       ║
╠════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  ACCOUNT STATUS                                                ║
║  ├─ Balance: $52,450.00 (+$2,450 / +4.9% today)               ║
║  ├─ Buying Power: $47,550.00                                  ║
║  ├─ Day Trades Used: 2 / 5                                    ║
║  └─ Margin Used: $0 (Cash account)                            ║
║                                                                 ║
║  OPEN POSITIONS (3)                                            ║
║  ┌──────┬─────────┬─────────┬─────────┬──────────┬──────────┐ ║
║  │Symbol│ Entry   │ Current │ P&L     │ Duration │ Conf     │ ║
║  ├──────┼─────────┼─────────┼─────────┼──────────┼──────────┤ ║
║  │ TSLA │ $245.20 │ $248.80 │ +$360   │ 45min    │ 72%      │ ║
║  │ NVDA │ $512.40 │ $511.10 │ -$130   │ 1h 23m   │ 68%      │ ║
║  │ SPY  │ $450.15 │ $451.20 │ +$105   │ 22min    │ 75%      │ ║
║  └──────┴─────────┴─────────┴─────────┴──────────┴──────────┘ ║
║                                                                 ║
║  WATCHLIST (24 symbols)                                        ║
║  Top Signals: AAPL (78% ↑), QQQ (71% ↑), META (69% ↓)        ║
║                                                                 ║
║  PERFORMANCE (Today)                                           ║
║  ├─ Trades: 8 (5 wins, 3 losses) = 62.5% win rate            ║
║  ├─ Profit Factor: 1.85                                       ║
║  ├─ Avg Win: +$480  Avg Loss: -$210                          ║
║  └─ Risk Limit: 0.9% / 3.0% used                             ║
║                                                                 ║
║  SYSTEM STATUS: ✓ All systems operational                     ║
╚════════════════════════════════════════════════════════════════╝
```

---

**Report Generated**: November 5, 2025
**Status**: IMPLEMENTATION PLAN READY
**Approval Required**: Proceed to Phase 7A (Short Horizon Validation)
