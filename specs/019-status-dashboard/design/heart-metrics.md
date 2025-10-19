# HEART Metrics: CLI Status Dashboard

**Feature**: `status-dashboard`
**Created**: 2025-10-19
**Measurement Window**: 7 days (rolling)

---

## HEART Framework

> **Goal**: Define measurable success criteria using Google's HEART framework.
> **Constraint**: All metrics MUST be Claude Code-measurable (logs, DB queries, no external dashboards).

### Metrics Table

| Dimension | Goal | Signal | Metric | Target | Guardrail | Measurement Source |
|-----------|------|--------|--------|--------|-----------|-------------------|
| **Happiness** | Reduce frustration from manual status checks | Dashboard launch frequency | Daily dashboard sessions | 5+ sessions/day | Min 3/day | `grep '"event":"dashboard.launched"' logs/dashboard-events.jsonl \| jq -r '.session_id' \| sort -u \| wc -l` |
| **Engagement** | Increase monitoring of trading performance | Session duration | Avg time viewing dashboard | 2-5 min/session | <10 min (avoid distraction) | `grep '"event":"dashboard.session_ended"' logs/dashboard-events.jsonl \| jq -r '.duration_sec' \| awk '{sum+=$1; count++} END {print sum/count}'` |
| **Adoption** | Replace manual log parsing | % of trading days using dashboard | Dashboard usage rate | 90% of trading days | Min 70% | `SELECT COUNT(DISTINCT DATE(created_at)) FROM dashboard_events WHERE event='dashboard.launched' AND created_at >= NOW() - INTERVAL '30 days'` |
| **Retention** | Maintain dashboard as primary monitoring tool | Consecutive days of usage | 7-day usage retention | 80% weekly use | Min 50% | `SELECT COUNT(DISTINCT user_id) FROM dashboard_events WHERE created_at >= NOW() - INTERVAL '7 days' AND created_at < NOW() - INTERVAL '14 days' AND user_id IN (SELECT user_id FROM dashboard_events WHERE created_at >= NOW() - INTERVAL '7 days')` |
| **Task Success** | Enable quick session health assessment | Time to answer "Am I meeting targets?" | Time-to-insight | <10 seconds | P95 <15s | Dashboard startup time from launch to first render: `grep '"event":"dashboard.first_render"' logs/dashboard-events.jsonl \| jq -r '.startup_ms' \| awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'` |

---

## Performance Targets

**Dashboard Startup**: <2 seconds (cold start)
- Measurement: Time from process start to first display render
- Query: `grep '"event":"dashboard.launched"' logs/dashboard-events.jsonl | jq -r '.startup_ms' | awk '{sum+=$1; count++} END {print sum/count/1000}'`

**Refresh Cycle**: <500ms (account data + trade log read)
- Measurement: Time to fetch and process data for display update
- Query: `grep '"event":"dashboard.refreshed"' logs/dashboard-events.jsonl | jq -r '.refresh_duration_ms' | awk '{sum+=$1; count++} END {print sum/count}'`

**Export Generation**: <1 second
- Measurement: Time to generate JSON + Markdown export files
- Query: `grep '"event":"dashboard.export"' logs/dashboard-events.jsonl | jq -r '.export_duration_ms' | awk '{sum+=$1; count++} END {print sum/count}'`

**Memory Footprint**: <50MB (long-running CLI tool)
- Measurement: Peak RSS memory during typical session
- Query: `grep '"event":"dashboard.memory_sample"' logs/dashboard-events.jsonl | jq -r '.memory_mb' | sort -rn | head -1`

---

## Hypothesis

**Problem**: Bot operators manually check account status via multiple API calls and parse trade logs using grep/jq to assess session performance, taking 3-5 minutes per check and performed 5-10 times per trading day
- Evidence: No unified monitoring tool, manual queries documented in trade-logging spec
- Impact: Context switching disrupts focus, delayed reaction to performance issues
- Gap: Cannot quickly answer "Am I meeting targets today?" or "What's my current risk exposure?"

**Solution**: Real-time CLI dashboard aggregating account data, position P&L, and performance metrics with target comparison in single view
- Change: Unified dashboard replaces manual API calls and log queries
- Mechanism: Polls account-data-module (leveraging 60s cache) and reads trade logs, displays in formatted sections with color coding
- Components: DashboardDisplay (rich rendering), MetricsCalculator (performance stats), TargetComparison (variance analysis), ExportGenerator (daily summaries)

**Prediction**: Unified dashboard will reduce session health assessment time from 3-5 minutes to <10 seconds
- Primary metric: Time-to-insight <10s (currently 3-5 minutes)
- Expected improvement: -96% reduction in assessment time
- Confidence: High (eliminates manual context assembly, industry-standard CLI dashboard pattern)

---

## Measurement Queries

### Log Patterns (structured JSON logs)

**Dashboard Sessions Per Day**:
```bash
# Count unique session IDs per day
grep '"event":"dashboard.launched"' logs/dashboard-events.jsonl | \
  jq -r '"\(.created_at | split("T")[0]) \(.session_id)"' | \
  awk '{sessions[$1]++} END {for (d in sessions) print d, sessions[d]}'
```

**Average Session Duration**:
```bash
# Calculate average session duration in minutes
grep '"event":"dashboard.session_ended"' logs/dashboard-events.jsonl | \
  jq -r '.duration_sec' | \
  awk '{sum+=$1; count++} END {printf "%.2f minutes\n", sum/count/60}'
```

**Export Usage Rate**:
```bash
# Count exports vs total sessions
total=$(grep '"event":"dashboard.launched"' logs/dashboard-events.jsonl | wc -l)
exports=$(grep '"event":"dashboard.export"' logs/dashboard-events.jsonl | wc -l)
echo "scale=2; ($exports / $total) * 100" | bc
```

**Performance P95 (Refresh Duration)**:
```bash
# Calculate 95th percentile refresh time
grep '"event":"dashboard.refreshed"' logs/dashboard-events.jsonl | \
  jq -r '.refresh_duration_ms' | \
  sort -n | \
  awk '{a[NR]=$1} END {print a[int(NR*0.95)] "ms"}'
```

**Error Rate**:
```bash
# Calculate error rate for dashboard operations
total=$(grep '"event":"dashboard.refreshed"' logs/dashboard-events.jsonl | wc -l)
errors=$(grep '"level":"error"' logs/dashboard-events.jsonl | grep dashboard | wc -l)
echo "scale=2; ($errors / $total) * 100" | bc
```

---

## Quality Gates

**Before Implementation**:
- [x] All HEART dimensions have targets defined
- [x] Measurement sources are log-based (Claude Code-accessible)
- [x] Hypothesis is specific and testable (-96% time reduction)
- [x] Guardrails protect against regressions (min 3 sessions/day, <10 min)

**After Implementation**:
- [ ] Dashboard logging instrumented (session start/end, refresh, export events)
- [ ] All metrics collected successfully for 7-day baseline
- [ ] Results compared to targets (pass/fail)
- [ ] Recommendation: Keep / Iterate / Rollback

---

## Notes

**Data Collection Setup**:
1. Structured JSON logging in `logs/dashboard-events.jsonl`
2. Event types: `dashboard.launched`, `dashboard.refreshed`, `dashboard.export`, `dashboard.session_ended`
3. Session correlation: Each session has unique UUID for tracking
4. Performance timing: All durations in milliseconds for precision

**Measurement Cadence**:
- Daily: Performance metrics (startup, refresh, export times)
- Weekly: HEART metrics (7-day rolling window)
- Per-session: Error rates, staleness indicators

**Success Criteria**:
- If Time-to-insight <10s: SUCCESS ✅
- If Daily sessions ≥5: SUCCESS ✅
- If Export usage >20%: SUCCESS ✅
- If Error rate <2%: SUCCESS ✅

---

**Template Version**: 1.0
**Last Updated**: 2025-10-19T17:30:00Z
