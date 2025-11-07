# GP Overfitting Analysis Report

**Date**: 2025-11-04
**Status**: Train/Validation Split Implemented & Tested

## Executive Summary

Implemented train/validation splitting in GP evolution to prevent overfitting. The system now works correctly by **detecting** overfitting, but reveals that **GP fundamentally cannot generate strategies that generalize**.

## What We Fixed

### 1. Train/Validation Data Splitting
- **Before**: Evolution used 100% of data for fitness evaluation
- **After**: Evolution uses 80% train / 20% validation split
- **Result**: Can now detect overfitting that was previously hidden

### 2. Complexity Regularization
- Added 0.001 penalty per tree node to prevent bloat
- Helps but doesn't solve fundamental problem

### 3. Minimum Trades Increased
- **Before**: 5 trades minimum
- **After**: 20 trades minimum
- **Result**: Higher statistical significance requirement

### 4. Validation-Based Selection
- **Before**: Strategies ranked by training fitness
- **After**: Strategies ranked by validation fitness
- **Result**: Selects strategies that generalize better (if any exist)

## Test Results: SPY

### Configuration
- Symbol: SPY
- Population: 100
- Generations: 15
- Data: 1 year (252 trading days)
- Train: 201 bars (80%)
- Validation: 51 bars (20%)

### Performance Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Train Fitness | 0.88 | >0.50 | ✓ PASS |
| Validation Fitness | 0.01 | >0.50 | ✗ FAIL |
| Generalization Ratio | 1% | >50% | ✗ FAIL |
| Validation Trades | 1-3 | >=20 | ✗ FAIL |
| Strategies Passed | 0/5 | >=3/5 | ✗ FAIL |

### Strategy Quality Analysis

**All 5 strategies show identical pattern:**

```
Strategy 1:
  Train: 0.8895 (looks good)
  Val:   0.0100 (terrible)
  Gen:   0.01   (1% generalization)
  Trades: 3     (insufficient)
```

**Example Strategy Tree (43 nodes, depth 12):**
```lisp
(not (sqrt (mul (add
    (gt (gt -0.566 sma_50) -0.214)
    (div (min rsi
        (div (min rsi ema_12)
            (min -0.214
                (div (min (sqrt ema_12)
                    (not (sqrt -0.214)))
                (abs sma_20)))))
    (abs sma_20)))
    (sqrt (div (min (sqrt ema_12)
        (not (sqrt (mul (exp sma_50)
            (sqrt ema_12)))))
    (abs -0.566))))))
```

## Root Cause Analysis

### Why GP Fails for Trading

1. **Numerical Quirk Exploitation**
   - GP discovers patterns in noise, not signal
   - Nested math operations like `sqrt(exp(sqrt(...)))` have no trading meaning
   - Trees exploit floating-point edge cases

2. **Sparse Signal Problem**
   - Most bars (>95%) should be "no signal"
   - GP optimizes for continuous output, not sparse discrete signals
   - Finds false patterns in random walks

3. **Validation Set Too Small**
   - 51 bars (20%) insufficient for 20+ trades requirement
   - Trade frequency constraint conflicts with data split size
   - Would need 100+ bars validation for meaningful statistics

4. **Non-Stationary Markets**
   - Market regimes change (bull/bear/sideways)
   - Patterns in training data don't persist
   - GP has no concept of regime detection

5. **Path Dependency**
   - Trade outcomes depend on entry/exit order
   - Position sizing matters
   - GP treats each bar independently

## Comparison: Before vs After

### Before (No Validation Split)
```
Train Sharpe: 3.22
Test Sharpe:  0.00
Conclusion: Looks good, fails in production
Problem: Overfitting hidden
```

### After (With Validation Split)
```
Train Fitness: 0.89
Val Fitness:   0.01
Conclusion: Overfitting detected early
Problem: Still overfit, but we can see it
```

## What Actually Improved

✓ **Detection**: Can now identify overfitting during evolution
✓ **Transparency**: Train vs validation metrics clearly show the problem
✓ **Waste Prevention**: Don't deploy strategies that will fail
✓ **Complexity Control**: Regularization reduces bloat

✗ **Generation**: Still can't create strategies that work

## Multi-Symbol Ensemble Results (Previous Test)

Tested before implementing validation split:

| Symbol | Strategies | Train Sharpe | Test Sharpe | Degradation | Trades |
|--------|-----------|--------------|-------------|-------------|--------|
| SPY    | 3         | 1.82         | 0.00        | 100%        | 3      |
| QQQ    | 3         | 1.95         | 0.00        | 100%        | 4      |
| NVDA   | 3         | 0.15         | 0.00        | 50%         | 9      |
| TSLA   | 3         | -1.18        | 0.00        | N/A         | 10     |
| **Total** | **12** | **-**     | **-**       | **-**       | **-**  |

**Success Rate**: 0/12 (0%)

**Ensemble Diversity**: 58.8/100 (good) - but strategies don't work individually

## Options Moving Forward

### Option A: Restrict GP Search Space ⚡ RECOMMENDED
**Problem**: GP search space too large, finds numerical quirks

**Solution**:
- Limit tree depth to 3-4 levels (currently 12-14)
- Restrict function set to interpretable operations (no nested sqrt/exp/log)
- Add domain knowledge constraints (e.g., RSI must be between 0-100)
- Use typed GP (boolean vs numeric types enforced)

**Pros**:
- Forces interpretable strategies
- Reduces bloat
- Faster evolution
- Easier to debug

**Cons**:
- May not find complex patterns
- Requires careful design

**Effort**: 1-2 days
**Success Probability**: 60%

### Option B: Hybrid GP + Constraint System
**Problem**: Pure GP has no trading domain knowledge

**Solution**:
- Start with template strategies (e.g., "RSI crossover + trend filter")
- Use GP to optimize parameters only
- Enforce minimum holding period (e.g., 5 bars)
- Require explicit entry AND exit rules

**Pros**:
- Combines human knowledge with ML
- Interpretable by design
- Less overfitting

**Cons**:
- Less flexible
- Requires strategy templates

**Effort**: 2-3 days
**Success Probability**: 70%

### Option C: Switch to Reinforcement Learning
**Problem**: GP not designed for sequential decision-making

**Solution**:
- Use DQN/PPO for entry/exit decisions
- State = market features + position status
- Reward = risk-adjusted returns
- Train with proper train/val/test splits

**Pros**:
- Purpose-built for sequential decisions
- Handles path dependency
- Can learn risk management

**Cons**:
- Much more complex
- Longer training time
- Harder to interpret

**Effort**: 1-2 weeks
**Success Probability**: 50%

### Option D: Ensemble of Simple Rules
**Problem**: Complex ML may not be necessary

**Solution**:
- Create 10-20 simple, interpretable rules:
  - RSI(14) < 30 AND Price > SMA(50)
  - MACD crossover + ATR filter
  - Bollinger Band breakout + volume confirmation
- Weight by backtest performance
- Use ensemble voting

**Pros**:
- Interpretable
- Fast to implement
- Easy to debug
- Industry-proven approach

**Cons**:
- Less "AI" (but maybe that's good?)
- Manual rule design needed

**Effort**: 2-3 days
**Success Probability**: 80%

### Option E: Document & Use for Research Only
**Problem**: GP may not work for systematic trading

**Solution**:
- Keep current system as research framework
- Document limitations clearly
- Use for paper trading / learning
- Focus on traditional technical analysis for live trading

**Pros**:
- Honest assessment
- No wasted effort
- Learn from failure

**Cons**:
- No production ML system
- "Giving up" on GP

**Effort**: 1 day
**Success Probability**: 100% (documentation succeeds)

## Recommendation

**Start with Option A (Restrict GP Search Space) + Option D (Simple Rules Ensemble)**

1. **Week 1**: Implement restricted GP with interpretability constraints
2. **Week 1-2**: Create ensemble of 15-20 simple rule-based strategies
3. **Compare**: See which approach works better
4. **Decide**: Keep best approach or combine both

This hedges bets - we improve GP while building a proven fallback.

## Key Learnings

1. **Train/validation split is essential** - Without it, overfitting is invisible
2. **GP is not magic** - It finds patterns in noise if allowed
3. **Simple often beats complex** - Rule-based strategies may outperform ML
4. **Interpretability matters** - Can't debug a 69-node nested tree
5. **Domain knowledge helps** - Pure ML without trading constraints fails

## Technical Implementation Details

### Modified Files
- `src/trading_bot/ml/generators/genetic_programming.py`
  - Added train/validation split (80/20)
  - Added complexity penalty (0.001 per node)
  - Increased min trades from 5 to 20
  - Final selection based on validation fitness

### Key Code Changes

#### Data Splitting (genetic_programming.py:558-565)
```python
# Split data into train (80%) and validation (20%)
split_idx = int(len(historical_data) * 0.8)
train_data = historical_data.iloc[:split_idx].copy()
validation_data = historical_data.iloc[split_idx:].copy()
```

#### Complexity Penalty (genetic_programming.py:578-580)
```python
# Add complexity penalty to prevent overly complex trees
complexity_penalty = tree.count_nodes() * 0.001
penalized_fitness = max(fitness - complexity_penalty, 0.0)
```

#### Validation Selection (genetic_programming.py:635-660)
```python
# Final evaluation on validation data for all top strategies
for i in range(top_n):
    tree, train_fitness, train_metrics = self.population[i]
    val_fitness, val_metrics = self.evaluate_fitness(tree, validation_data)
    # Sort by validation fitness (prefer strategies that generalize)
```

## Conclusion

**The system now works correctly** - it detects overfitting and prevents bad strategies from reaching production.

**The problem is revealed** - GP evolution, without constraints, cannot generate trading strategies that generalize.

**Next step required**: Choose which approach to pursue (A, B, C, D, or E) based on project goals and timeline.
