# Multi-Track Strategy Development Plan (A+C+D)

**Date**: 2025-11-04
**Goal**: Build robust strategy generation system with 3 parallel approaches
**Timeline**: 2-3 weeks

## Overview

Implement three complementary approaches simultaneously:
- **Track A**: Constrained GP (Restricted Search Space)
- **Track C**: Reinforcement Learning (DQN/PPO)
- **Track D**: Rule-Based Ensemble (Simple Interpretable Rules)

Final deliverable: Meta-ensemble that combines best performers from all three tracks.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Strategy Generator System                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Track A    │  │   Track C    │  │   Track D    │      │
│  │ Constrained  │  │ Reinforcement│  │  Rule-Based  │      │
│  │     GP       │  │   Learning   │  │   Ensemble   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│         ├──────────────────┴──────────────────┤              │
│         │                                      │               │
│  ┌──────▼──────────────────────────────────────▼─────┐      │
│  │         Strategy Selection & Validation            │      │
│  │  - Walk-forward validation                         │      │
│  │  - Performance comparison                          │      │
│  │  - Correlation analysis                            │      │
│  └──────┬──────────────────────────────────────────┬─┘      │
│         │                                           │         │
│  ┌──────▼───────────────────────────────────────────▼───┐   │
│  │             Meta-Ensemble Builder                     │   │
│  │  - Combines best from each track                     │   │
│  │  - Correlation-weighted allocation                   │   │
│  │  - Adaptive rebalancing                              │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Week 1: Foundation + Quick Wins

### Day 1-2: Track D - Rule-Based Ensemble (PRIORITY 1)

**Why First**: Fastest to implement, highest success rate (80%), proven approach

#### Simple Rule Templates
Create 15-20 interpretable strategies:

**Momentum Strategies (5)**
1. RSI Oversold: `RSI(14) < 30 AND Price > SMA(50)`
2. RSI Overbought Short: `RSI(14) > 70 AND Price < SMA(50)`
3. MACD Bullish Cross: `MACD crosses above Signal AND MACD < 0`
4. MACD + Trend: `MACD > Signal AND Price > SMA(200)`
5. Momentum + Volume: `Price > SMA(20) AND Volume > SMA(20, Volume) * 1.5`

**Mean Reversion Strategies (5)**
6. Bollinger Bounce: `Price < BB_Lower AND RSI < 40`
7. Bollinger Breakout: `Price > BB_Upper AND Volume > Avg * 2`
8. SMA Deviation: `(Price - SMA(20)) / SMA(20) < -0.05`
9. Z-Score Reversion: `Z-Score(Close, 20) < -2`
10. Channel Breakout: `Price > Donchian_Upper(20)`

**Volatility Strategies (5)**
11. ATR Expansion: `ATR(14) > SMA(ATR, 50) * 1.5 AND RSI > 50`
12. Low Vol Breakout: `ATR < Avg(ATR) * 0.7 AND Price > SMA(50)`
13. Keltner Channel: `Price > Keltner_Upper AND Volume confirmed`
14. ADX Trend: `ADX > 25 AND +DI > -DI AND Price > SMA(50)`
15. Volatility Squeeze: `BB_Width < SMA(BB_Width, 20) * 0.5 AND Price > SMA(20)`

**Implementation Steps**:
1. Create `RuleBasedStrategy` class
2. Implement each rule with clear entry/exit logic
3. Backtest each rule individually
4. Build ensemble voting system (weighted by Sharpe)
5. Test on multi-symbol data

**Expected Results**:
- 60-70% of rules show positive Sharpe on validation
- Ensemble Sharpe: 1.5-2.5
- Drawdown: 10-15%

**Files to Create**:
- `src/trading_bot/ml/generators/rule_based.py`
- `src/trading_bot/ml/rules/` (directory with individual rule implementations)
- `src/trading_bot/ml/ensemble_voting.py`

### Day 3-4: Track A - Constrained GP (PRIORITY 2)

**Why Second**: Builds on existing GP, moderate effort, 60% success rate

#### Constraints to Implement

**1. Tree Depth Limit**
```python
MAX_DEPTH = 3  # Down from 12-14
```

**2. Restricted Function Set**
```python
# Remove: sqrt, exp, log (numerical exploits)
# Keep: and, or, not, gt, lt, gte, lte
FUNCTIONS = ['and', 'or', 'not', 'gt', 'lt', 'gte', 'lte']
```

**3. Typed Operators**
```python
# Boolean operations only on boolean values
# Comparison operations return boolean
# No nested math operations
class TypedGPNode:
    type: Literal['boolean', 'numeric', 'indicator']
```

**4. Domain Constraints**
```python
# RSI must be compared to 0-100 range
# Price comparisons must use moving averages
# Volume must be normalized
CONSTRAINTS = {
    'rsi': (0, 100),
    'macd': (-10, 10),
    'volume': 'normalize_only'
}
```

**5. Minimum Holding Period**
```python
# Strategy must hold position for at least N bars
MIN_HOLD_PERIOD = 5
```

**Implementation Steps**:
1. Create `ConstrainedGPGenerator` class extending current GP
2. Implement typed tree nodes
3. Add constraint validation during crossover/mutation
4. Increase population to 200 (smaller search space)
5. Test on SPY with train/validation split

**Expected Results**:
- Simpler, interpretable trees (max 15 nodes)
- Better generalization (30-50% train→val retention)
- 2-3 strategies passing validation

**Files to Modify**:
- `src/trading_bot/ml/generators/genetic_programming.py` (add ConstrainedGPGenerator)
- `src/trading_bot/ml/config.py` (add constraint config)

### Day 5-7: Track C Foundation - RL System Design

**Why Last**: Longest timeline (2 weeks total), but most innovative

#### System Design

**State Space** (12 dimensions):
```python
state = [
    rsi_14,                    # Momentum
    macd, macd_signal,         # Trend
    price_to_sma20,            # Position
    price_to_sma50,
    atr_normalized,            # Volatility
    volume_ratio,
    returns_5d, returns_20d,   # Recent performance
    position_status,           # 0=flat, 1=long, -1=short
    bars_in_position,          # Holding period
    unrealized_pnl             # Current P&L
]
```

**Action Space** (3 actions):
```python
actions = [
    0: HOLD / DO_NOTHING,
    1: BUY / ENTER_LONG,
    2: SELL / EXIT_LONG
]
```

**Reward Function**:
```python
reward = (
    realized_pnl * 1.0          # Profit/loss on closed trades
    - abs(action - prev_action) * 0.01  # Penalize excessive trading
    - max_drawdown * 0.5        # Penalize drawdown
    + sharpe_ratio * 0.3        # Reward risk-adjusted returns
)
```

**Architecture**: DQN (Deep Q-Network)
```
Input (12) → Dense(128, ReLU) → Dense(64, ReLU) → Dense(32, ReLU) → Output(3)
```

**Implementation Steps**:
1. Create `RLTradingEnvironment` (OpenAI Gym interface)
2. Implement DQN agent with experience replay
3. Design reward shaping for risk management
4. Set up training loop with early stopping

**Expected Results**:
- Learns basic buy-low-sell-high patterns
- Better at risk management than GP
- Sharpe 1.0-2.0 after training

**Files to Create**:
- `src/trading_bot/ml/rl/environment.py`
- `src/trading_bot/ml/rl/dqn_agent.py`
- `src/trading_bot/ml/rl/train.py`

## Week 2: Implementation & Training

### Days 8-10: Complete All Tracks

**Track D**: Finalize rule ensemble, optimize weights
**Track A**: Run restricted GP evolution on 4 symbols (SPY, QQQ, NVDA, TSLA)
**Track C**: Train DQN for 50K episodes on SPY

### Days 11-12: Validation & Comparison

**Walk-Forward Validation** on all strategies:
- 4 rolling windows (3 months train, 1 month test)
- Metrics: Sharpe, Sortino, Max DD, Win Rate, Profit Factor

**Correlation Analysis**:
```python
# Build correlation matrix between strategies
# Identify diversification opportunities
corr_matrix = calculate_strategy_correlations(all_strategies)
```

### Days 13-14: Meta-Ensemble Construction

**Selection Criteria**:
1. Validation Sharpe > 1.0
2. Max Drawdown < 20%
3. Minimum 30 trades in validation period
4. Generalization ratio > 50%

**Weighting Method**: Inverse Variance + Correlation Adjustment
```python
weights = optimize_portfolio(
    returns=strategy_returns,
    method='sharpe_weighted',
    correlation_penalty=0.3
)
```

## Week 3: Optimization & Production

### Days 15-17: Fine-Tuning

**Track D**: Parameter optimization for top rules
**Track A**: Additional GP runs with different constraints
**Track C**: Hyperparameter tuning, longer training

### Days 18-19: Integration Testing

- Test meta-ensemble on completely held-out data (6 months)
- Paper trading simulation
- Risk analysis (VaR, CVaR)

### Day 20-21: Documentation & Deployment

- Performance comparison report
- Strategy explanations
- Deployment guide

## Success Metrics

### Individual Track Targets

| Track | Success Criteria | Min | Target | Stretch |
|-------|-----------------|-----|--------|---------|
| D (Rules) | Strategies Passing | 8/15 | 12/15 | 15/15 |
| D (Rules) | Ensemble Sharpe | 1.2 | 2.0 | 2.5 |
| A (GP) | Strategies Passing | 3/20 | 8/20 | 12/20 |
| A (GP) | Generalization | 30% | 50% | 70% |
| C (RL) | Validation Sharpe | 0.8 | 1.5 | 2.0 |
| C (RL) | Max Drawdown | <25% | <15% | <10% |

### Meta-Ensemble Targets

| Metric | Min | Target | Stretch |
|--------|-----|--------|---------|
| Validation Sharpe | 1.5 | 2.5 | 3.0 |
| Max Drawdown | <20% | <12% | <8% |
| Win Rate | 55% | 65% | 70% |
| Strategies in Ensemble | 10 | 20 | 30 |
| Avg Correlation | <0.5 | <0.3 | <0.2 |

## Resource Requirements

### Dependencies to Install
```bash
# RL libraries
pip install torch gymnasium stable-baselines3

# Additional ML
pip install scikit-optimize optuna

# Visualization
pip install plotly tensorboard
```

### Computational Resources
- **Track D**: CPU only, ~1 hour
- **Track A**: CPU, ~2-3 hours per symbol
- **Track C**: GPU recommended (RTX 3060+), ~8-12 hours training

## Risk Management

### What Could Go Wrong

**Track D Risk**: Rules overfit to historical regime
- **Mitigation**: Test on multiple market conditions (bull/bear/sideways)
- **Fallback**: Use only rules that work in all regimes

**Track A Risk**: Constraints too restrictive, no good strategies
- **Mitigation**: Try multiple constraint sets in parallel
- **Fallback**: Relax depth limit to 4-5 if needed

**Track C Risk**: RL doesn't converge or learns degenerate policies
- **Mitigation**: Careful reward shaping, baseline comparisons
- **Fallback**: Use simpler Q-learning or policy gradient methods

## Comparison Framework

After all tracks complete, evaluate on same test data:

```python
comparison_report = {
    'track_d_rules': {
        'strategies': 15,
        'passed_validation': 12,
        'ensemble_sharpe': 2.1,
        'diversity_score': 45.0
    },
    'track_a_gp': {
        'strategies': 20,
        'passed_validation': 6,
        'ensemble_sharpe': 1.8,
        'diversity_score': 62.0
    },
    'track_c_rl': {
        'agents': 3,
        'best_sharpe': 1.6,
        'avg_sharpe': 1.3,
        'stability': 'good'
    },
    'meta_ensemble': {
        'total_strategies': 25,
        'final_sharpe': 2.7,
        'diversity_score': 68.0,
        'composition': {
            'track_d': 0.50,  # 50% weight
            'track_a': 0.30,  # 30% weight
            'track_c': 0.20   # 20% weight
        }
    }
}
```

## Decision Points

### After Week 1
- **If Track D succeeds alone (Sharpe > 2.0)**: Consider stopping and deploying
- **If all tracks struggling**: Reevaluate approach, consider Option E (research only)

### After Week 2
- **If Track C failing**: Reallocate time to improving D and A
- **If Track A not improving**: Focus on D + C only

## Expected Outcomes

### Best Case
- Track D: 12/15 rules pass, Sharpe 2.3
- Track A: 8/20 strategies pass, Sharpe 1.9
- Track C: Agent achieves Sharpe 1.7
- Meta-ensemble: Sharpe 2.8, DD 9%, 68% diversity

### Realistic Case
- Track D: 10/15 rules pass, Sharpe 1.9
- Track A: 5/20 strategies pass, Sharpe 1.4
- Track C: Agent achieves Sharpe 1.2
- Meta-ensemble: Sharpe 2.2, DD 13%, 55% diversity

### Worst Case
- Track D: 8/15 rules pass, Sharpe 1.5
- Track A: 2/20 strategies pass, Sharpe 0.9
- Track C: Agent doesn't converge
- Fallback to Track D only: Sharpe 1.5, DD 15%

Even worst case gives us a working system (Track D).

## Next Steps

1. **Immediate**: Start Track D - create RuleBasedStrategy class
2. **Day 2**: Implement first 5 momentum rules
3. **Day 3**: Test rules individually, build ensemble
4. **Day 4**: Begin Track A - add constraints to GP
5. **Day 5**: Design RL environment

Ready to begin?
