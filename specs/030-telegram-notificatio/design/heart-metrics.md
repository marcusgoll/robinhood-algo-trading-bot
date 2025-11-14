# HEART Metrics: Telegram Notifications

**Feature**: 030-telegram-notificatio
**Created**: 2025-10-27
**Measurement Period**: 30 days post-launch

## Overview
Telegram notification system for trading bot alerts and updates. Metrics focus on delivery reliability, trader engagement, and operational impact.

## 1. Happiness: Notification Reliability

**What we're measuring**: Trader satisfaction with notification delivery speed and accuracy.

**Metric**: Notification delivery success rate
- **Target**: 99% delivery success rate (notifications delivered within 10 seconds)
- **Baseline**: N/A (new feature)
- **Expected Improvement**: Establish baseline reliability standard

**Measurement Source**:
```python
# Application logs with notification events
# File: logs/notifications-*.jsonl

# Query delivery success rate
grep '"event":"telegram_notification"' logs/notifications-*.jsonl | \
  jq -r '.success' | \
  awk '{success+=$1; total++} END {print "Success Rate: " success/total*100"%"}'

# Query delivery latency (P50, P95, P99)
grep '"event":"telegram_notification"' logs/notifications-*.jsonl | \
  jq -r '.latency_ms' | \
  sort -n | \
  awk '{
    values[NR] = $1;
    sum += $1;
  } END {
    printf "P50: %.0fms\n", values[int(NR*0.5)];
    printf "P95: %.0fms\n", values[int(NR*0.95)];
    printf "P99: %.0fms\n", values[int(NR*0.99)];
    printf "Mean: %.0fms\n", sum/NR;
  }'
```

**Validation Method**: Manual spot checks - compare Telegram notification timestamps with trade log timestamps.

---

## 2. Engagement: Notification Usefulness

**What we're measuring**: Whether traders find notifications valuable enough to keep them enabled.

**Metric**: Feature retention rate (traders keep Telegram enabled)
- **Target**: 90% of traders who enable notifications keep them enabled after 30 days
- **Baseline**: N/A (new feature)
- **Expected Improvement**: High retention = notifications are useful

**Measurement Source**:
```python
# Track TELEGRAM_ENABLED configuration over time
# File: internal tracking (configuration audit log)

# At Day 0: Record users who enable feature
# At Day 30: Count users who still have TELEGRAM_ENABLED=true

retention_rate = users_enabled_at_day_30 / users_enabled_at_day_0

# Alternative (if no audit log):
# Survey: "Are Telegram notifications still valuable to you after 30 days?" (Yes/No)
```

**Validation Method**: User interviews after 2 weeks to understand notification value and pain points.

---

## 3. Adoption: Feature Activation Rate

**What we're measuring**: How quickly traders adopt the new notification feature.

**Metric**: Configuration completion rate
- **Target**: 80% of active traders configure Telegram notifications within first week
- **Baseline**: N/A (new feature)
- **Expected Improvement**: High adoption = feature addresses real need

**Measurement Source**:
```python
# Check .env configuration presence
# Manual audit or startup log analysis

# Count users with TELEGRAM_BOT_TOKEN configured
enabled_users = count(TELEGRAM_ENABLED=true AND TELEGRAM_BOT_TOKEN != empty)

# Count total active users (ran bot in last 7 days)
active_users = count(last_startup_timestamp > now() - 7 days)

adoption_rate = enabled_users / active_users

# Log at startup:
# {"event": "telegram_config_status", "enabled": true, "timestamp": "..."}
```

**Validation Method**: Track configuration documentation visits (README section on Telegram setup).

---

## 4. Retention: Continued Usage

**What we're measuring**: Sustained value of notifications over time (same as Engagement metric).

**Metric**: 30-day retention rate (see Engagement above)
- **Target**: 90% retention after 30 days
- **Baseline**: N/A
- **Expected Improvement**: High retention = feature is sticky

**Measurement Source**: Same as Engagement section.

**Validation Method**: Monthly check-ins with traders to understand evolving notification needs.

---

## 5. Task Success: Timely Awareness of Trading Events

**What we're measuring**: Whether notifications enable faster trader response to critical events.

**Metric**: Time-to-awareness for critical events (circuit breakers, major losses)
- **Target**: 95% of critical events result in trader awareness within 5 minutes
- **Baseline**: Console-only monitoring (~30+ min awareness delay, based on manual log checking)
- **Expected Improvement**: -83% time-to-awareness (30min → 5min)

**Measurement Source**:
```python
# Combine event timestamp with trader intervention timestamp
# File: logs/trading-events-*.jsonl + manual trader action logs

# For circuit breaker events:
# 1. Extract event timestamp from logs
event_time = grep '"event":"circuit_breaker_triggered"' logs/*.jsonl | jq -r '.timestamp'

# 2. Extract trader intervention timestamp (manual action log or /stop command)
intervention_time = grep '"event":"trader_intervention"' logs/*.jsonl | jq -r '.timestamp'

# 3. Calculate response time
response_time = intervention_time - event_time

# 4. Success = response within 5 minutes
success_rate = count(response_time <= 5min) / total_critical_events
```

**Validation Method**: Survey traders on notification timeliness and usefulness for decision-making.

---

## Measurement Schedule

**Daily**: Monitor delivery success rate and latency (automated alert if <95%)
**Weekly**: Check adoption rate for new users
**Monthly**: Calculate retention rate and task success metrics
**Quarterly**: Review all metrics and adjust thresholds based on actual usage

---

## Success Thresholds

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Delivery Success Rate | ≥99% | <95% | <90% |
| Delivery Latency (P95) | ≤10s | >20s | >60s |
| Adoption Rate (7 days) | ≥80% | <60% | <40% |
| Retention Rate (30 days) | ≥90% | <75% | <50% |
| Time-to-Awareness | ≤5min | >10min | >30min |

**Action on Critical**: Investigate root cause, survey users, consider feature improvements.

---

## Notes
- Telegram API does not expose read receipts, so engagement is measured via retention proxy
- Time-to-awareness baseline (30min) estimated from manual log monitoring patterns
- Retention and engagement metrics are closely related (both measure sustained value)
- All metrics require logging instrumentation in notification service
