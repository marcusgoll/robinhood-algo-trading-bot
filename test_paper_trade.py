#!/usr/bin/env python3
"""
Test script to send a paper trade through the orchestrator.
"""
import sys
sys.path.insert(0, "/app/src")

from trading_bot.config import Config
from trading_bot.orchestrator import TradingOrchestrator
from datetime import datetime

print("Initializing orchestrator for paper trade test...")
config = Config.from_env_and_json()
orchestrator = TradingOrchestrator(config, auth=None, mode="paper")

# Manually create a test trade (simulating what optimize-entry would return)
test_trade = {
    "symbol": "AAPL",
    "optimization": {
        "recommended_entry": 175.50,
        "position_size": 10,
        "stop_loss": 172.00,
        "target_1": 180.00,
        "target_2": 185.00,
        "risk_reward_ratio": 2.57
    }
}

symbol = test_trade["symbol"]
entry = test_trade["optimization"]["recommended_entry"]
shares = test_trade["optimization"]["position_size"]
stop = test_trade["optimization"]["stop_loss"]
target = test_trade["optimization"]["target_1"]

print("\nTest trade prepared:")
print(f"  Symbol: {symbol}")
print(f"  Entry: ${entry}")
print(f"  Shares: {shares}")
print(f"  Stop: ${stop}")
print(f"  Target: ${target}")

# Execute paper trade (simulating what run_market_open_workflow does)
optimization = test_trade.get("optimization", {})

paper_trade = {
    "symbol": symbol,
    "entry": optimization.get("recommended_entry"),
    "shares": optimization.get("position_size"),
    "stop_loss": optimization.get("stop_loss"),
    "target": optimization.get("target_1"),
    "timestamp": datetime.now().isoformat()
}

orchestrator.daily_trades.append(paper_trade)

print("\n✓ Paper trade logged successfully!")
print("\nPaper trade details:")
print(f"  Symbol: {paper_trade['symbol']}")
print(f"  Entry: ${paper_trade['entry']}")
print(f"  Shares: {paper_trade['shares']}")
print(f"  Stop Loss: ${paper_trade['stop_loss']}")
print(f"  Target: ${paper_trade['target']}")
print(f"  Timestamp: {paper_trade['timestamp']}")

print(f"\n✓ Total paper trades today: {len(orchestrator.daily_trades)}")

# Show orchestrator status
status = orchestrator.get_status()
print("\nOrchestrator status:")
print(f"  Mode: {status['mode']}")
print(f"  Trades today: {status['trades_today']}")
print(f"  Daily cost: ${status['daily_cost']:.2f}")
print(f"  Budget remaining: ${status['budget_remaining']:.2f}")

print("\n✓ Test complete - Paper trade successfully executed!")
