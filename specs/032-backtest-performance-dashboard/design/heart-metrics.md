# HEART Metrics: Backtest Performance Dashboard

**Feature**: Backtest Performance Dashboard with Equity Curves
**Created**: 2025-10-28
**Owner**: Trading Bot Team

## Overview

HEART metrics framework for measuring user-centered success of the backtest dashboard feature. Focus on strategy optimization workflow efficiency and decision-making quality.

---

## 1. Happiness (User Satisfaction)

**Metric**: Dashboard visualization clarity score

**Target**: 4.5/5.0 satisfaction rating

**Measure**:
- User survey after first use: "How satisfied are you with the backtest dashboard?"
- 5-point Likert scale (Very Dissatisfied → Very Satisfied)
- Survey triggers after user views 3+ backtest reports

**Current Baseline**: N/A (new feature)

**Why This Matters**: Clear visualizations reduce cognitive load when analyzing strategy performance, leading to faster insights and confident decision-making.

---

## 2. Engagement (Usage Frequency)

**Metric**: Weekly active backtest analysts (users viewing dashboard ≥1x/week)

**Target**: 80% of traders use dashboard weekly

**Measure**:
```sql
SELECT COUNT(DISTINCT user_id) / (SELECT COUNT(*) FROM users WHERE role='trader')
FROM dashboard_page_views
WHERE page = '/backtests'
  AND viewed_at >= NOW() - INTERVAL '7 days'
```

**Current Baseline**: 0% (feature doesn't exist yet)

**Why This Matters**: High engagement indicates the dashboard provides ongoing value in strategy refinement, not just one-time curiosity.

---

## 3. Adoption (New User Activation)

**Metric**: Traders who run first backtest within 7 days of bot activation

**Target**: 60% adoption within first week

**Measure**:
```sql
SELECT COUNT(DISTINCT user_id) / (SELECT COUNT(*) FROM users WHERE created_at >= '2025-11-01')
FROM backtests
WHERE created_at <= user.created_at + INTERVAL '7 days'
```

**Current Baseline**: ~20% estimated (manual backtest runs, no dashboard)

**Why This Matters**: Early adoption indicates onboarding success and immediate perceived value of backtesting workflow.

---

## 4. Retention (Repeat Usage)

**Metric**: 30-day backtest dashboard retention rate

**Target**: 70% of users return to dashboard within 30 days

**Measure**:
```sql
WITH first_view AS (
  SELECT user_id, MIN(viewed_at) AS first_viewed
  FROM dashboard_page_views
  WHERE page = '/backtests'
  GROUP BY user_id
),
return_view AS (
  SELECT DISTINCT fv.user_id
  FROM first_view fv
  JOIN dashboard_page_views dpv
    ON fv.user_id = dpv.user_id
    AND dpv.page = '/backtests'
    AND dpv.viewed_at BETWEEN fv.first_viewed + INTERVAL '7 days'
                           AND fv.first_viewed + INTERVAL '30 days'
)
SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM first_view) AS retention_pct
FROM return_view
```

**Current Baseline**: N/A (new feature)

**Why This Matters**: Repeat visits indicate sustained value, not novelty effect. Indicates users find dashboard useful for ongoing strategy iteration.

---

## 5. Task Success (Completion Rate)

**Metric**: Backtest comparison completion rate

**Target**: 75% of users who start comparison complete export

**Measure**:
```sql
SELECT
  COUNT(DISTINCT CASE WHEN action = 'export_comparison' THEN session_id END) * 100.0 /
  COUNT(DISTINCT CASE WHEN action = 'start_comparison' THEN session_id END) AS completion_pct
FROM dashboard_events
WHERE event_type = 'comparison_flow'
  AND timestamp >= NOW() - INTERVAL '30 days'
```

**Current Baseline**: 0% (no comparison feature exists)

**Why This Matters**: Completing comparison workflow indicates users successfully evaluated multiple strategies and made informed decisions about which to deploy.

**Secondary Metric**: Average time to first insight (load dashboard → make strategy decision)

**Target**: <3 minutes to identify best performing strategy

**Measure**: Time between `/backtests/:id` page load and export action
```sql
SELECT AVG(
  EXTRACT(EPOCH FROM (export_time - page_load_time))
) / 60 AS avg_minutes_to_insight
FROM (
  SELECT
    session_id,
    MIN(CASE WHEN action = 'page_load' THEN timestamp END) AS page_load_time,
    MIN(CASE WHEN action = 'export_report' THEN timestamp END) AS export_time
  FROM dashboard_events
  WHERE page = '/backtests/:id'
  GROUP BY session_id
  HAVING MIN(CASE WHEN action = 'export_report' THEN timestamp END) IS NOT NULL
) insights
```

---

## Measurement Infrastructure

**Required Instrumentation**:
1. Page view tracking (`dashboard_page_views` table)
   - `user_id`, `page`, `viewed_at`, `session_id`

2. Event tracking (`dashboard_events` table)
   - `user_id`, `session_id`, `event_type`, `action`, `timestamp`, `metadata`

3. User surveys (post-feature-use trigger)
   - Popup after 3 backtest views: "Rate your experience"

**Implementation Notes**:
- Use existing logging infrastructure (JSON logs) for event capture
- Weekly aggregation queries for HEART dashboard
- No PII collection (user_id hashed for privacy)

---

## Success Thresholds

| Metric | Launch (Month 1) | Growth (Month 3) | Maturity (Month 6) |
|--------|------------------|------------------|---------------------|
| Happiness | 4.0/5.0 | 4.3/5.0 | 4.5/5.0 |
| Engagement | 50% weekly | 70% weekly | 80% weekly |
| Adoption | 40% in 7 days | 50% in 7 days | 60% in 7 days |
| Retention | 50% at 30 days | 60% at 30 days | 70% at 30 days |
| Task Success | 60% completion | 70% completion | 75% completion |

---

## Review Cadence

- **Weekly**: Check engagement and task success rates
- **Monthly**: Full HEART report with trends
- **Quarterly**: User interviews for qualitative feedback

**Owner**: Product Manager (with data analyst support)
**Stakeholders**: Trading team, Dev team, UX designer
