# Visual References: Startup Sequence

## Overview

This document contains visual references and console output mockups for the startup sequence feature. Since this is a CLI-based feature, visuals consist of console output examples.

## Console Output Mockups

### Successful Startup (Paper Trading)

```
════════════════════════════════════════════════════════════
         ROBINHOOD TRADING BOT - STARTUP SEQUENCE
════════════════════════════════════════════════════════════
Mode: PAPER TRADING (Simulation - No Real Money)
Constitution: v1.0.0
════════════════════════════════════════════════════════════

[✓] Loading configuration...
[✓] Validating credentials...
[✓] Initializing logging system...
[✓] Initializing mode switcher (PAPER mode)...
[✓] Initializing circuit breakers...
[✓] Verifying component health...

════════════════════════════════════════════════════════════
✅ STARTUP COMPLETE - Ready to trade
════════════════════════════════════════════════════════════
Current Phase: experience
Max Trades Today: 999
Circuit Breaker: Active (Max Loss: 3%, Max Consecutive: 3)
Startup Duration: 2.3 seconds
Timestamp: 2025-10-08 14:23:45 UTC

Waiting for market hours (7:00 AM - 10:00 AM EST)...
```

### Failed Startup (Missing Credentials)

```
════════════════════════════════════════════════════════════
         ROBINHOOD TRADING BOT - STARTUP SEQUENCE
════════════════════════════════════════════════════════════

[✓] Loading configuration...
[✗] Validation failed: Missing required credentials

❌ STARTUP BLOCKED

Error: ROBINHOOD_USERNAME not found in .env file

Remediation steps:
  1. Copy .env.example to .env
  2. Set ROBINHOOD_USERNAME in .env
  3. Set ROBINHOOD_PASSWORD in .env
  4. Re-run: python -m src.trading_bot.main

For help, see: README.md (Security section)
```

### Phase-Mode Conflict Error

```
════════════════════════════════════════════════════════════
         ROBINHOOD TRADING BOT - STARTUP SEQUENCE
════════════════════════════════════════════════════════════

[✓] Loading configuration...
[✗] Validation failed: Phase-mode conflict

❌ STARTUP BLOCKED

Error: Live trading not allowed in "experience" phase

Remediation steps:
  1. Change mode to "paper" in config.json, OR
  2. Advance to "proof" phase (requires 10-20 profitable sessions)

Safety: Constitution §Safety_First blocks live trading in experience phase
```

### Dry-Run Mode

```
════════════════════════════════════════════════════════════
         ROBINHOOD TRADING BOT - STARTUP VALIDATION
════════════════════════════════════════════════════════════
Mode: DRY-RUN (Validation Only - No Trading)
════════════════════════════════════════════════════════════

[✓] Loading configuration...
[✓] Validating credentials...
[✓] Initializing logging system...
[✓] Initializing mode switcher (PAPER mode)...
[✓] Initializing circuit breakers...
[✓] Verifying component health...

════════════════════════════════════════════════════════════
✅ VALIDATION COMPLETE - Configuration is ready
════════════════════════════════════════════════════════════
All systems validated successfully
Startup Duration: 1.8 seconds

Dry-run mode: Exiting without starting trading loop
```

### JSON Output Mode

```json
{
  "status": "ready",
  "mode": "paper",
  "phase": "experience",
  "startup_duration_seconds": 2.3,
  "timestamp": "2025-10-08T14:23:45Z",
  "components": {
    "config": {
      "status": "ready",
      "errors": []
    },
    "logging": {
      "status": "ready",
      "errors": []
    },
    "mode_switcher": {
      "status": "ready",
      "mode": "paper",
      "phase": "experience",
      "can_switch_to_live": false
    },
    "circuit_breaker": {
      "status": "ready",
      "max_daily_loss_pct": 3.0,
      "max_consecutive_losses": 3,
      "is_tripped": false
    },
    "trading_bot": {
      "status": "ready",
      "is_running": false,
      "paper_trading": true
    }
  },
  "errors": [],
  "warnings": [
    "ROBINHOOD_MFA_SECRET not configured - manual MFA required during authentication"
  ]
}
```

## Visual Design Principles

### Box-Drawing Characters

Using Unicode box-drawing characters for visual hierarchy:
- `═` (double horizontal line) - Major sections
- `║` (double vertical line) - Not used in current design
- Standard ASCII for compatibility fallback

### Progress Indicators

- `[✓]` - Success (green if ANSI supported)
- `[✗]` - Failure (red if ANSI supported)
- `[⚠]` - Warning (yellow if ANSI supported)

**Fallback** (no Unicode): `[OK]`, `[FAIL]`, `[WARN]`

### Color Coding (Optional ANSI)

If terminal supports ANSI colors:
- **Green**: Success messages, checkmarks
- **Red**: Errors, failure indicators
- **Yellow**: Warnings, cautions
- **Cyan**: Section headers, banners
- **White**: Default text

**Implementation**: Detect terminal capability, gracefully degrade to plain text

### Alignment and Spacing

- **Banner Width**: 60 characters (fits 80-column terminals with margin)
- **Indentation**: 2 spaces for nested content
- **Padding**: 1 blank line between major sections
- **Right-Align**: Values (e.g., "2.3 seconds")

## Layout Measurements

```
Banner:
  Width: 60 characters
  Top padding: 0 lines
  Bottom padding: 1 line
  Center alignment: Yes

Progress Steps:
  Prefix: "[✓] " (4 chars)
  Description: Left-aligned
  Spacing between steps: Single line

Summary Section:
  Label width: 20 characters
  Value alignment: Left (after label)
  Key-value pairs: "Label: Value"

Error Messages:
  Header: "❌ STARTUP BLOCKED" (centered)
  Error detail: 2-space indent
  Remediation: Numbered list, 2-space indent per item
```

## UX Patterns

### Progressive Disclosure

1. **Start Simple**: Show banner and mode immediately
2. **Step-by-Step**: Display each initialization step as it executes
3. **Summarize**: Final summary with all key parameters
4. **Guide on Error**: Specific remediation steps for failures

### Error Remediation

Every error must include:
1. **What failed**: Clear error message
2. **Why it matters**: Context (e.g., "Constitution §Safety_First requires...")
3. **How to fix**: Numbered, actionable steps
4. **Where to learn more**: Reference to docs

### Feedback Timing

- **Immediate**: Progress indicators appear as each step executes
- **Sub-second**: Each step should complete in <1 second for responsive feel
- **Total**: Complete startup in <5 seconds

## Accessibility

- **Screen Readers**: All Unicode characters have ASCII fallback
- **No Color**: Information conveyed via text, not color alone
- **High Contrast**: Box-drawing characters provide visual structure

## References

- **Similar Patterns**: Docker container startup, npm install, pytest execution
- **Box Drawing**: Unicode U+2550 (═), U+2551 (║), U+2554-U+255D (corners)
- **Terminal Detection**: Check `sys.stdout.isatty()`, `os.getenv("TERM")`
