# Ensemble Analysis Report: Diverse_Multi_Symbol_Ensemble

**Created:** 2025-11-04 03:22:14 UTC
**Number of strategies:** 8
**Aggregation method:** weighted_avg

## Diversity Metrics

- **Average correlation:** 0.41
- **Diversity score:** 58.8/100
- **Weight concentration:** 0.13 (lower = more balanced)

## Expected Performance

- **Expected Sharpe:** 3.22
- **Expected return:** 85.3%
- **Expected max drawdown:** 8.3%

## Component Strategies

| # | Strategy | Weight | Sharpe | Max DD | Win Rate |
|---|----------|--------|--------|--------|----------|
| 1 | SPY_GP_Strategy_1 | 12.5% | 3.22 | 2.1% | 86.4% |
| 2 | SPY_GP_Strategy_2 | 12.5% | 3.22 | 2.1% | 86.4% |
| 3 | QQQ_GP_Strategy_1 | 13.5% | 3.48 | 3.5% | 95.2% |
| 4 | QQQ_GP_Strategy_2 | 13.5% | 3.48 | 3.5% | 95.2% |
| 5 | NVDA_GP_Strategy_1 | 12.1% | 3.12 | 7.3% | 87.5% |
| 6 | NVDA_GP_Strategy_2 | 12.1% | 3.12 | 7.3% | 87.5% |
| 7 | TSLA_GP_Strategy_1 | 11.8% | 3.05 | 8.3% | 83.3% |
| 8 | TSLA_GP_Strategy_2 | 11.8% | 3.05 | 8.3% | 83.3% |

## Correlation Matrix

Strategy pairwise correlations:

```
     S 1 S 2 S 3 S 4 S 5 S 6 S 7 S 8
S 1  1.00 1.00 0.25 0.25 0.30 0.30 0.45 0.45
S 2  1.00 1.00 0.25 0.25 0.30 0.30 0.45 0.45
S 3  0.25 0.25 1.00 1.00 0.20 0.20 0.32 0.32
S 4  0.25 0.25 1.00 1.00 0.20 0.20 0.32 0.32
S 5  0.30 0.30 0.20 0.20 1.00 1.00 0.37 0.37
S 6  0.30 0.30 0.20 0.20 1.00 1.00 0.37 0.37
S 7  0.45 0.45 0.32 0.32 0.37 0.37 1.00 1.00
S 8  0.45 0.45 0.32 0.32 0.37 0.37 1.00 1.00
```

## Recommendations

✓ Good diversity - acceptable for ensemble
✓ Well-balanced weights across strategies
✓ Strong expected risk-adjusted returns

## Symbol Distribution

| Symbol | Count | Percentage |
|--------|-------|------------|
| SPY | 2 | 25.0% |
| QQQ | 2 | 25.0% |
| NVDA | 2 | 25.0% |
| TSLA | 2 | 25.0% |

