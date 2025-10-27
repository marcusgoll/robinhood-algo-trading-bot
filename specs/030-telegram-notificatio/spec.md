# Feature Specification: Telegram Notifications

**Branch**: `feature/030-telegram-notificatio`
**Created**: 2025-10-27
**Status**: Draft

## User Scenarios

### Primary User Story
A day trader running an automated trading bot wants to receive real-time notifications on their mobile device when critical trading events occur (position entries/exits, risk alerts, performance milestones, system errors) so they can monitor their bot's activity and intervene if needed without constantly watching the terminal.

### Acceptance Scenarios
1. **Given** the bot places a new position, **When** the order executes, **Then** the trader receives a Telegram message with ticker, entry price, position size, and stop loss
2. **Given** a position hits the stop loss or take profit, **When** the exit executes, **Then** the trader receives a Telegram message with exit details and P&L
3. **Given** a risk management circuit breaker triggers (max daily loss or consecutive losses), **When** the bot halts trading, **Then** the trader receives an urgent Telegram alert with breach details
4. **Given** the bot encounters a critical error (authentication failure, API connection loss, data feed interruption), **When** the error occurs, **Then** the trader receives a Telegram error notification with diagnostic information
5. **Given** daily/weekly trading performance milestones, **When** the time boundary occurs, **Then** the trader receives a Telegram summary report with win rate, total P&L, and key metrics

### Edge Cases
- What happens when Telegram API is unavailable or rate-limited?
- How does system handle notification failures without blocking trading operations?
- What if user has not set up Telegram credentials in environment variables?
- How to prevent notification spam during high-frequency trading periods?
- What happens when bot runs in paper trading mode vs live mode (different notification urgency)?
- How to handle rich formatting (bold, code blocks, emoji) in Telegram messages?

## User Stories (Prioritized)

> **Purpose**: Break down feature into independently deliverable stories for MVP-first delivery.
> **Format**: [P1] = MVP (ship first), [P2] = Enhancement, [P3] = Nice-to-have

### Story Prioritization

**Priority 1 (MVP) 🎯**
- **US1** [P1]: As a trader, I want to receive Telegram notifications when positions are opened so that I know when my bot enters new trades
  - **Acceptance**:
    - Sends message on successful position entry
    - Includes: ticker, entry price, shares/contracts, position size ($), stop loss, target
    - Distinguishes between paper trading and live trading
    - Non-blocking: notification failure does not prevent trade execution
  - **Independent test**: Can send position entry notification via Telegram Bot API
  - **Effort**: M (4-8 hours)

- **US2** [P1]: As a trader, I want to receive Telegram notifications when positions are closed so that I can track my trading results in real-time
  - **Acceptance**:
    - Sends message on position exit (stop loss, take profit, manual close)
    - Includes: ticker, exit price, exit reason, P&L ($), P&L (%), duration
    - Color-codes profit (green ✅) vs loss (red ❌)
    - Non-blocking: notification failure does not prevent trade execution
  - **Independent test**: Can send position exit notification with P&L calculation
  - **Effort**: M (4-8 hours)

- **US3** [P1]: As a trader, I want to receive urgent Telegram alerts when risk circuit breakers trigger so that I can take immediate action if my bot stops trading
  - **Acceptance**:
    - Sends high-priority alert on circuit breaker events (max daily loss, consecutive losses)
    - Includes: breach type, current value, threshold, timestamp
    - Uses urgent emoji (🚨) and bold formatting
    - Non-blocking: notification failure does not affect circuit breaker logic
  - **Independent test**: Can send urgent alert with formatted message
  - **Effort**: S (2-4 hours)

**Priority 2 (Enhancement)**
- **US4** [P2]: As a trader, I want to receive Telegram notifications for system errors so that I can troubleshoot issues without monitoring logs
  - **Acceptance**:
    - Sends notification on critical errors (authentication failure, API connection loss, data feed errors)
    - Includes: error type, error message, timestamp, affected component
    - Rate-limits error notifications (max 1 per error type per hour) to prevent spam
    - Non-blocking: notification failure does not affect error handling
  - **Depends on**: US1 (uses same notification infrastructure)
  - **Effort**: S (2-4 hours)

- **US5** [P2]: As a trader, I want to receive daily/weekly performance summary notifications so that I can review my bot's performance without opening the terminal
  - **Acceptance**:
    - Sends scheduled summary at configurable time (default: end of trading day 4 PM EST)
    - Includes: total trades, win rate, total P&L, best/worst trade, current positions
    - Supports daily and weekly summaries (configurable)
    - Respects timezone configuration from PERFORMANCE_SUMMARY_TIMEZONE
  - **Depends on**: US1, US2 (aggregates position data)
  - **Effort**: M (4-8 hours)

**Priority 3 (Nice-to-have)**
- **US6** [P3]: As a trader, I want to receive Telegram notifications for momentum signals so that I can be alerted to potential trading opportunities
  - **Acceptance**:
    - Sends notification when high-confidence momentum signal detected
    - Includes: ticker, signal type (catalyst/pre-market/pattern), strength score, key metrics
    - Configurable threshold for notification (e.g., only score >80)
    - Non-blocking and rate-limited (max 5 signals per hour)
  - **Depends on**: US1, Feature 002 (momentum detection)
  - **Effort**: S (2-4 hours)

- **US7** [P3]: As a trader, I want to send commands to my bot via Telegram (start/stop trading, check status) so that I can control my bot remotely
  - **Acceptance**:
    - Bot listens for Telegram commands from authorized chat ID
    - Supports commands: /status, /stop, /start, /positions
    - Requires authentication (only responds to configured chat ID)
    - Returns confirmation message with action result
  - **Depends on**: US1 (bidirectional Telegram communication)
  - **Effort**: L (8-16 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (core notifications for trades and risk events), validate delivery reliability, then add error notifications (US4) and performance summaries (US5). Defer momentum signals (US6) and bidirectional commands (US7) based on usage patterns.

## Visual References

Not applicable - backend notification system with no UI components.

## Success Metrics (HEART Framework)

### Happiness: Notification reliability
- **Target**: 99% delivery success rate (notifications delivered within 10 seconds of trigger)
- **Measure**:
  ```python
  # Log notification attempts and results
  delivery_rate = successful_sends / total_attempts
  # Query from application logs
  grep '"event":"telegram_notification"' logs/*.jsonl | jq -r '.success' | awk '{success+=$1; total++} END {print success/total*100"%"}'
  ```
- **Baseline**: N/A (new feature)

### Engagement: Notification usefulness
- **Target**: Traders check Telegram notifications for >80% of critical events (entries/exits/alerts)
- **Measure**:
  ```python
  # Track notification opens/reads (Telegram API does not expose read receipts)
  # Alternative: Survey traders after 2 weeks of usage
  # Proxy metric: Retention of feature (disable rate <10%)
  ```
- **Baseline**: N/A (qualitative feedback from initial users)

### Adoption: Feature activation rate
- **Target**: 80% of active traders configure Telegram notifications within first week
- **Measure**:
  ```python
  # Check .env configuration
  enabled_users = count(TELEGRAM_BOT_TOKEN in .env)
  adoption_rate = enabled_users / total_active_users
  ```
- **Baseline**: N/A (new feature)

### Retention: Continued usage
- **Target**: 90% of traders who enable notifications keep them enabled after 30 days
- **Measure**:
  ```python
  # Track TELEGRAM_ENABLED flag changes over time
  retention_rate = users_still_enabled_at_30_days / users_enabled_at_day_0
  ```
- **Baseline**: N/A (new feature)

### Task Success: Timely awareness of trading events
- **Target**: 95% of critical events (position exits, circuit breakers) result in trader awareness within 5 minutes
- **Measure**:
  ```python
  # Combine notification delivery time with trader response time
  # Proxy: Time-to-intervention for critical events
  avg_response_time = mean(intervention_timestamp - event_timestamp)
  success_rate = count(response_time <= 5min) / total_critical_events
  ```
- **Baseline**: N/A (compare against console-only monitoring - likely 30+ min awareness delay)

## Screens Inventory (UI Features Only)

> **SKIP SCREENS**: Backend-only feature (no UI components). Notifications are delivered via Telegram mobile/desktop app.

## Hypothesis

> **Not an improvement feature**: This is a new capability addition, not improving an existing flow.

## Context Strategy & Signal Design

- **System prompt altitude**: Moderate technical context (Telegram Bot API, async messaging, error handling)
- **Tool surface**: Essential tools - Telegram Bot API (python-telegram-bot or requests), logging, environment config
- **Examples in scope**:
  1. Position entry notification with formatted message
  2. Circuit breaker alert with urgent formatting
  3. Error notification with rate limiting
- **Context budget**: Target 20k tokens (notification service is focused and isolated)
- **Retrieval strategy**: Upfront for Telegram API patterns and message formatting, JIT for integration points
- **Memory artifacts**: NOTES.md with API patterns, TODO.md for integration tasks
- **Compaction cadence**: Minimal (feature is self-contained)
- **Sub-agents**: None - single-agent implementation

## Requirements

### Functional (testable only)

- **FR-001**: System MUST send Telegram notifications without blocking trading operations (async delivery with timeout)
- **FR-002**: System MUST support Telegram Bot API authentication via environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- **FR-003**: System MUST send position entry notifications with required fields: ticker, entry price, shares, position size ($), stop loss, target
- **FR-004**: System MUST send position exit notifications with required fields: ticker, exit price, exit reason, P&L ($), P&L (%), trade duration
- **FR-005**: System MUST send circuit breaker alerts with required fields: breach type, current value, threshold, timestamp
- **FR-006**: System MUST gracefully degrade when Telegram credentials are not configured (log warning, continue trading)
- **FR-007**: System MUST handle Telegram API failures without crashing trading operations (catch exceptions, log errors)
- **FR-008**: System MUST support Telegram message formatting (Markdown or HTML) for rich text (bold, code, emoji)
- **FR-009**: System MUST distinguish between paper trading and live trading in notification messages
- **FR-010**: System MUST respect message size limits (Telegram max: 4096 characters, truncate or split if needed)

### Non-Functional (testable only)

- **NFR-001**: Notification delivery latency MUST be <10 seconds from trigger to Telegram delivery (P95)
- **NFR-002**: System MUST maintain >99% notification delivery success rate under normal conditions
- **NFR-003**: Notification service MUST NOT consume >5% of CPU time (trading operations take priority)
- **NFR-004**: System MUST rate-limit error notifications (max 1 per error type per hour) to prevent spam
- **NFR-005**: Telegram credentials (bot token) MUST be stored securely in environment variables, never in code
- **NFR-006**: System MUST log all notification attempts (success/failure) for debugging and metrics

### Assumptions
- Trader has created a Telegram bot via BotFather and obtained bot token
- Trader has identified their chat ID (can be obtained via /start message to bot)
- Telegram Bot API is accessible from bot's deployment environment (no firewall restrictions)
- Default notification format is Markdown (can be changed to HTML if needed)
- Daily summary notifications scheduled at end of trading day (4 PM EST), configurable via environment variable
- Notifications include timezone-aware timestamps (use PERFORMANCE_SUMMARY_TIMEZONE from .env)
- Paper trading notifications include "[PAPER]" prefix to distinguish from live trading
- Position exit reason can be: "Stop Loss", "Take Profit", "Manual Close", "End of Day", "Circuit Breaker"

### Out of Scope
- Multi-user support (single chat ID per bot instance)
- Interactive Telegram commands (bidirectional communication) - deferred to US7
- Rich media (charts, images) - text-only notifications for MVP
- Custom notification templates (use fixed format for MVP)
- Notification history/persistence (Telegram chat serves as history)
- SMS or email notifications (Telegram only for MVP)

## Success Criteria

> **Purpose**: Define measurable, technology-agnostic, user-focused, verifiable outcomes.

- **SC-001**: Traders receive position entry notifications on their mobile device within 10 seconds of trade execution with accurate trade details
- **SC-002**: Traders receive position exit notifications with correct P&L calculation (validated against broker records)
- **SC-003**: Traders receive urgent alerts within 5 seconds when risk circuit breakers trigger
- **SC-004**: Notification system operates with 99% reliability (less than 1% message delivery failures over 30 days)
- **SC-005**: Trading operations continue without interruption when Telegram API is unavailable or misconfigured
- **SC-006**: Error notifications are rate-limited to prevent spam (traders receive max 1 notification per error type per hour)
- **SC-007**: Traders can distinguish paper trading notifications from live trading notifications at a glance
- **SC-008**: Daily performance summaries are delivered at configured time with accurate metrics

## Deployment Considerations

**Platform Dependencies**:
- None (pure Python implementation, no platform-specific features)

**Environment Variables** (REQUIRED):
New section in .env.example:
```bash
# ============================================
# TELEGRAM NOTIFICATIONS (Feature 030)
# ============================================
# Telegram bot for real-time trading notifications

# Enable/disable Telegram notifications
TELEGRAM_ENABLED=false  # Set to 'true' after configuring bot token and chat ID

# Telegram Bot API credentials
TELEGRAM_BOT_TOKEN=  # Get from @BotFather on Telegram (format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)
TELEGRAM_CHAT_ID=  # Your chat ID (numeric, get via /start message or @userinfobot)

# Notification preferences
TELEGRAM_NOTIFY_POSITIONS=true  # Position entry/exit notifications
TELEGRAM_NOTIFY_ALERTS=true  # Circuit breaker and risk alerts
TELEGRAM_NOTIFY_ERRORS=true  # System error notifications
TELEGRAM_NOTIFY_SUMMARIES=true  # Daily/weekly performance summaries
TELEGRAM_SUMMARY_TIME=16:00  # Time for daily summary (24-hour format, uses PERFORMANCE_SUMMARY_TIMEZONE)

# Message formatting
TELEGRAM_PARSE_MODE=Markdown  # Options: Markdown, HTML, None
TELEGRAM_INCLUDE_EMOJIS=true  # Use emojis in messages (📈, 📉, 🚨, ✅, ❌)

# Rate limiting
TELEGRAM_ERROR_RATE_LIMIT_MINUTES=60  # Max 1 notification per error type per N minutes
```

**Breaking Changes**:
- No breaking changes (additive feature)

**Migration Required**:
- No database migrations
- No data backfill

**Python Dependencies** (add to requirements.txt):
```bash
# Telegram notifications (Feature 030)
python-telegram-bot==20.7  # Telegram Bot API wrapper
```

**Rollback Considerations**:
- Standard rollback (remove notification calls, set TELEGRAM_ENABLED=false)
- No data loss risk (notifications are ephemeral)
- Trading operations unaffected by rollback (non-blocking design)

## Dependencies
- External: Telegram Bot API (https://core.telegram.org/bots/api)
- Internal: Existing alert/event system (src/trading_bot/performance/alerts.py)
- Python library: python-telegram-bot (async Telegram wrapper)

## Open Questions

None - specification is complete with reasonable defaults for ambiguous details.

## Notes
- Specification informed by research of existing codebase structure and patterns
- Alert integration points identified in performance module
- Environment variable pattern follows established convention
- Non-blocking design critical for maintaining trading operation reliability
- Feature aligns with recent LLM integration (Feature 029) for enhanced observability
