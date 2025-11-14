#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick validation test for risk management position calculation."""

import sys
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

from src.trading_bot.risk_management.manager import RiskManager
from src.trading_bot.risk_management.config import RiskManagementConfig
from decimal import Decimal

print("=" * 60)
print("RISK MANAGEMENT VALIDATION TEST")
print("=" * 60)
print("\nTesting: Position plan calculation with pullback detection")
print("\nScenario:")
print("  - Symbol: TSLA")
print("  - Entry price: $250.30")
print("  - Account balance: $100,000")
print("  - Risk per trade: 1.0%")
print("  - Price data with pullback low at $248.00")

config = RiskManagementConfig.default()
manager = RiskManager(config=config)

# Sample price data with pullback low at $248.00
# Note: Swing low detection requires: prev + low + 2 confirmation candles = minimum 4 candles
price_data = [
    {"timestamp": "2025-01-01 09:28", "low": 249.50, "close": 250.00},  # Previous high
    {"timestamp": "2025-01-01 09:29", "low": 248.50, "close": 248.80},  # Pullback starts
    {"timestamp": "2025-01-01 09:30", "low": 248.00, "close": 248.50},  # Swing low (bottom)
    {"timestamp": "2025-01-01 09:31", "low": 249.00, "close": 249.50},  # Confirmation 1 (higher low)
    {"timestamp": "2025-01-01 09:32", "low": 249.50, "close": 250.30},  # Confirmation 2 (higher low)
]

print("\n" + "-" * 60)
print("CALCULATING POSITION PLAN...")
print("-" * 60)

try:
    plan = manager.calculate_position_with_stop(
        symbol="TSLA",
        entry_price=Decimal("250.30"),
        account_balance=Decimal("100000"),
        account_risk_pct=1.0,
        price_data=price_data
    )

    print("\n[SUCCESS] POSITION PLAN CALCULATED SUCCESSFULLY\n")
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Symbol:          {plan.symbol}")
    print(f"Entry Price:     ${plan.entry_price}")
    print(f"Stop Price:      ${plan.stop_price}")
    print(f"Target Price:    ${plan.target_price}")
    print(f"Quantity:        {plan.quantity} shares")
    print(f"Risk Amount:     ${plan.risk_amount}")
    print(f"Reward Amount:   ${plan.reward_amount}")
    print(f"Reward Ratio:    {plan.reward_ratio}:1")
    print(f"Pullback Source: {plan.pullback_source}")
    if plan.pullback_price:
        print(f"Pullback Price:  ${plan.pullback_price}")
    print(f"Created At:      {plan.created_at}")

    print("\n" + "=" * 60)
    print("VALIDATION CHECKS")
    print("=" * 60)

    # Expected values
    expected_stop = Decimal("248.00")
    expected_quantity = 434  # Approximate
    expected_target = Decimal("254.90")  # Approximate
    expected_risk = Decimal("1000")  # Approximate

    checks = []

    # Check 1: Stop price matches pullback low
    if plan.stop_price == expected_stop:
        checks.append(("[PASS]", f"Stop price is ${expected_stop} (pullback low detected)"))
    else:
        checks.append(("[FAIL]", f"Stop price is ${plan.stop_price}, expected ${expected_stop}"))

    # Check 2: Quantity is approximately correct
    if 430 <= plan.quantity <= 440:
        checks.append(("[PASS]", f"Quantity is {plan.quantity} shares (within expected range 430-440)"))
    else:
        checks.append(("[FAIL]", f"Quantity is {plan.quantity}, expected ~{expected_quantity}"))

    # Check 3: Target price is approximately correct (2:1 ratio)
    if Decimal("254.50") <= plan.target_price <= Decimal("255.50"):
        checks.append(("[PASS]", f"Target price is ${plan.target_price} (2:1 risk-reward ratio)"))
    else:
        checks.append(("[FAIL]", f"Target price is ${plan.target_price}, expected ~${expected_target}"))

    # Check 4: Risk is approximately 1% of account
    if Decimal("990") <= plan.risk_amount <= Decimal("1010"):
        checks.append(("[PASS]", f"Risk is ${plan.risk_amount} (~1% of $100k account)"))
    else:
        checks.append(("[FAIL]", f"Risk is ${plan.risk_amount}, expected ~${expected_risk}"))

    # Check 5: Reward ratio is approximately 2:1 (allow for rounding)
    if plan.reward_ratio >= 1.95:  # Within 2.5% of 2:1 ratio
        checks.append(("[PASS]", f"Reward ratio is {plan.reward_ratio}:1 (meets 2:1 minimum)"))
    else:
        checks.append(("[FAIL]", f"Reward ratio is {plan.reward_ratio}:1, expected >= 2:1"))

    # Check 6: Pullback was detected (not fallback)
    if plan.pullback_source == "detected":
        checks.append(("[PASS]", f"Pullback source is '{plan.pullback_source}' (swing low found)"))
    else:
        checks.append(("[WARN]", f"Pullback source is '{plan.pullback_source}' (fallback used)"))

    for status, message in checks:
        print(f"{status} {message}")

    # Summary
    passed = sum(1 for status, _ in checks if status == "[PASS]")
    total = len(checks)

    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY: {passed}/{total} checks passed")
    print("=" * 60)

    if passed == total:
        print("\n[SUCCESS] ALL VALIDATION CHECKS PASSED!")
        print("\n[PASS] AC-001: Entry with automatic stop-loss - VERIFIED")
        print("[PASS] Position sizing calculation - VERIFIED")
        print("[PASS] Pullback detection - VERIFIED")
        print("[PASS] Risk-reward ratio - VERIFIED")
        print("\nRisk management feature is working correctly!")
        exit(0)
    else:
        print(f"\n[WARN] {total - passed} validation check(s) failed")
        print("Review the results above for details")
        exit(1)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    exit(1)
