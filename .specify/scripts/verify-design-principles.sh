#!/bin/bash

echo "=== Jobs Principles Verification ==="

# 1. Spacing audit (8px grid)
echo "[1/5] Checking spacing (8px grid)..."
VIOLATIONS=$(grep -r "gap-\|p-\|m-\|space-" apps/web/mock/ 2>/dev/null | \
  grep -v "gap-\(0\|1\|2\|3\|4\|6\|8\|12\|16\|20\|24\)" | \
  wc -l)
if [ "$VIOLATIONS" -eq 0 ]; then
  echo "✅ PASS: All spacing on 8px grid"
else
  echo "❌ FAIL: $VIOLATIONS spacing violations found"
  echo "   Run: grep -r \"gap-\|p-\|m-\|space-\" apps/web/mock/ | grep -v \"gap-\(0\|1\|2\|3\|4\|6\|8\|12\|16\|20\|24\)\" to see violations"
fi

# 2. Animation audit (200-300ms)
echo "[2/5] Checking animations (200-300ms)..."
VIOLATIONS=$(grep -r "transition\|animate" apps/web/mock/ 2>/dev/null | \
  grep -v "duration-\(200\|250\|300\)" | \
  wc -l)
if [ "$VIOLATIONS" -eq 0 ]; then
  echo "✅ PASS: All transitions 200-300ms"
else
  echo "❌ FAIL: $VIOLATIONS timing violations found"
  echo "   Run: grep -r \"transition\|animate\" apps/web/mock/ | grep -v \"duration-\(200\|250\|300\)\" to see violations"
fi

# 3. Tooltip audit (zero tooltips = obvious design)
echo "[3/5] Checking tooltips (should be 0)..."
TOOLTIPS=$(grep -r "Tooltip\|HelpCircle\|QuestionMark" apps/web/mock/ 2>/dev/null | wc -l)
if [ "$TOOLTIPS" -eq 0 ]; then
  echo "✅ PASS: Zero tooltips (design is obvious)"
else
  echo "⚠️  WARN: $TOOLTIPS tooltips found (design may be unclear)"
  echo "   Run: grep -r \"Tooltip\|HelpCircle\|QuestionMark\" apps/web/mock/ to see tooltips"
fi

# 4. Primary CTA audit (1 per screen)
echo "[4/5] Checking primary CTAs (1 per screen)..."
# This requires manual verification
echo "⚠️  MANUAL: Review each screen in mock/ for ≤1 primary CTA"
echo "   Check: grep -r 'Button.*primary\|<button.*primary' apps/web/mock/ | wc -l per screen"

# 5. Click count audit (≤2 clicks)
echo "[5/5] Checking click paths (≤2 clicks)..."
echo "⚠️  MANUAL: Test each flow, verify ≤2 clicks to complete"

echo ""
echo "=== Summary ==="
echo "Run time tests: 5 users, <10s each, 0 questions asked"
echo "Document results in: specs/NNN-feature/design/crit.md"
