"""
Test evening optimizer with autonomy level 2 (bounded - auto-applies high confidence proposals)
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

from llm_optimizer import LLMOptimizer
from market_context import MarketContextBuilder

print("="*80)
print("EVENING OPTIMIZER TEST - Autonomy Level 2 (Bounded)")
print("="*80)

# Initialize optimizer at level 2 (bounded autonomy)
optimizer = LLMOptimizer(
    api_key_anthropic=os.getenv('ANTHROPIC_API_KEY'),
    autonomy_level=2  # Auto-apply high-confidence proposals
)

print("\n[OK] Optimizer initialized (Level 2 - Bounded Autonomy)")
print("  High-confidence proposals (>70%) will be auto-applied")

# Load performance data
print("\nLoading performance data...")
with open('llm_trading/performance/performance_latest.json', 'r') as f:
    performance = json.load(f)

print(f"[OK] Performance data loaded:")
print(f"  Total trades: {performance['summary']['total_trades']}")
print(f"  Win rate: {performance['summary']['win_rate']:.1%}")
print(f"  Total P&L: ${performance['summary']['total_pnl']:.2f}")

# Load watchlist
print("\nLoading watchlist...")
with open('watchlists/watchlist_latest.json', 'r') as f:
    watchlist_data = json.load(f)

print(f"[OK] Watchlist loaded: {len(watchlist_data['watchlist'])} stocks")

# Get market context
print("\nBuilding market context...")
context_builder = MarketContextBuilder(
    os.getenv('ALPACA_API_KEY'),
    os.getenv('ALPACA_SECRET_KEY')
)
spy_context = context_builder.build_full_context('SPY')

market_context = spy_context['market_context']
print(f"[OK] Market context built:")
print(f"  SPY trend: {market_context['spy_trend']}")
print(f"  Market regime: {market_context['regime']}")

# Run optimization
print("\n" + "="*80)
print("RUNNING OPTIMIZATION")
print("="*80)

report = optimizer.optimize_strategy(
    performance_data=performance,
    watchlist_data=watchlist_data,
    market_conditions=market_context
)

print("\n" + "="*80)
print("OPTIMIZATION COMPLETE")
print("="*80)

# Display summary
if 'applied_changes' in report:
    print(f"\n[OK] Applied {len(report['applied_changes'])} changes")
    for change in report['applied_changes']:
        print(f"  • {change['parameter']}: {change.get('old_value', '?')} -> {change['new_value']}")

if 'rejected_changes' in report:
    print(f"\n[X] Rejected {len(report['rejected_changes'])} changes (low confidence)")

print("\n[OK] Optimizer test complete!")
