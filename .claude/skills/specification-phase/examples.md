# Specification Phase Examples

Good specs vs bad specs, showing what makes effective specifications.

## Good Spec Examples (0-2 Clarifications)

### Example 1: User Authentication with OAuth2

**Feature**: "Add OAuth2 authentication for user login"

**Classification**:
- HAS_UI: true (login screen, callback handler)
- IS_IMPROVEMENT: false (new feature)
- HAS_METRICS: false (auth is infrastructure)
- HAS_DEPLOYMENT_IMPACT: true (env variables for OAuth keys)

**Spec Quality Markers**:
- ✅ Clear scope: "User login only, admin auth out of scope"
- ✅ Informed guesses: "Session duration: 30 days (standard web app default)"
- ✅ Concrete success criteria: "User can log in via Google OAuth in <5 seconds"
- ✅ Only 1 clarification: "[NEEDS CLARIFICATION: Should we support GitHub OAuth alongside Google?]"
- ✅ Deployment section: "Requires OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET env vars"

**Why it's good**:
- Scope is explicit (user auth only, not admin)
- Uses informed guesses for standard patterns (session duration)
- Success criteria is measurable (<5 seconds)
- Only asks about critical scope decision (GitHub support)
- Documents deployment requirements upfront

---

### Example 2: Background Job to Process Uploads

**Feature**: "Create background worker to process file uploads"

**Classification**:
- HAS_UI: false (backend-only worker)
- IS_IMPROVEMENT: false (new feature)
- HAS_METRICS: false (infrastructure)
- HAS_DEPLOYMENT_IMPACT: true (requires job queue setup)

**Spec Quality Markers**:
- ✅ Clear scope: "Handles CSV and PDF only, images out of scope"
- ✅ Informed guesses: "Retry: 3 attempts with exponential backoff (industry standard)"
- ✅ Concrete success criteria: "Process 100 files/hour with <1% failure rate"
- ✅ Zero clarifications (all decisions have reasonable defaults)
- ✅ Error handling: "Log to error-log.md + monitoring system"

**Why it's good**:
- Classification correctly identified as backend-only (no UI)
- Uses industry-standard defaults (retry logic)
- Success criteria is quantifiable (100 files/hour, <1% failure)
- No unnecessary clarifications (all technical defaults documented)
- Error handling pattern clearly specified

---

### Example 3: Student Progress Dashboard

**Feature**: "Add student progress dashboard showing completion rates"

**Classification**:
- HAS_UI: true (dashboard screen)
- IS_IMPROVEMENT: false (new feature)
- HAS_METRICS: true (tracks user engagement with dashboard)
- HAS_DEPLOYMENT_IMPACT: false (no breaking changes)

**Spec Quality Markers**:
- ✅ Clear scope: "Read-only dashboard, editing features out of scope"
- ✅ Informed guesses: "Lighthouse Performance Score: ≥85 (standard web app)"
- ✅ HEART metrics: "Engagement: ≥60% of teachers view dashboard weekly"
- ✅ Only 2 clarifications:
  - "[NEEDS CLARIFICATION: Should dashboard show all students or only assigned classes?]"
  - "[NEEDS CLARIFICATION: Should parents have access to this dashboard?]"
- ✅ UI mockups: "See visuals/dashboard-wireframe.png"

**Why it's good**:
- Scope is explicit (read-only, no editing)
- Uses standard performance targets (Lighthouse ≥85)
- HEART metrics define success (≥60% engagement)
- Only asks about scope-defining decisions (audience and data access)
- UI artifacts referenced for design clarity

---

## Bad Spec Examples (>5 Clarifications)

### Example 1: Export User Data Feature

**Feature**: "Allow users to export their data"

**Classification**:
- HAS_UI: true (export button)
- IS_IMPROVEMENT: false (new feature)
- HAS_METRICS: false
- HAS_DEPLOYMENT_IMPACT: false

**Spec Quality Issues**:
- ❌ **7 clarifications** (limit: 3):
  1. [NEEDS CLARIFICATION: What format? CSV, JSON, PDF, Excel?]
  2. [NEEDS CLARIFICATION: Which fields to export?]
  3. [NEEDS CLARIFICATION: Email notification on completion?]
  4. [NEEDS CLARIFICATION: Rate limiting strategy?]
  5. [NEEDS CLARIFICATION: Maximum file size?]
  6. [NEEDS CLARIFICATION: Retention period for generated files?]
  7. [NEEDS CLARIFICATION: Should we compress large exports?]
- ❌ Vague success criteria: "System exports data correctly"
- ❌ No informed guesses for standard patterns
- ❌ No performance targets

**Why it's bad**:
- Too many clarifications for non-critical decisions
- Questions 1, 4, 5, 6, 7 have reasonable defaults (JSON, 10/day, 50MB, 24h, yes)
- Success criteria is not measurable ("correctly" is subjective)
- Missing performance targets (how fast should export complete?)

**How to fix**:
- Use informed guesses: "Format: CSV (most compatible), JSON as alternate"
- Use standard defaults: "Rate limit: 10 exports/day per user (prevents abuse)"
- Keep only critical clarification: "[NEEDS CLARIFICATION: Which user fields should be included?]"
- Add measurable criteria: "User receives download link within 30 seconds for <10k records"

---

### Example 2: Improve Search Performance

**Feature**: "Make search faster"

**Classification**:
- HAS_UI: false (backend optimization)
- IS_IMPROVEMENT: true (optimization)
- HAS_METRICS: false (should be true!)
- HAS_DEPLOYMENT_IMPACT: false (should be true if changing DB!)

**Spec Quality Issues**:
- ❌ **Wrong classification**: Missing HAS_METRICS=true (performance improvement needs measurement)
- ❌ **Wrong classification**: Missing HAS_DEPLOYMENT_IMPACT=true if adding indexes
- ❌ Vague baseline: "Current search is slow"
- ❌ Vague target: "Search should be faster"
- ❌ **5 clarifications**:
  1. [NEEDS CLARIFICATION: How fast should it be?]
  2. [NEEDS CLARIFICATION: Which database to use?]
  3. [NEEDS CLARIFICATION: Should we cache results?]
  4. [NEEDS CLARIFICATION: What about fuzzy matching?]
  5. [NEEDS CLARIFICATION: Pagination size?]

**Why it's bad**:
- Classification missed improvement flag (needs baseline + target hypothesis)
- No concrete baseline: "slow" is not measurable
- No concrete target: "faster" is not measurable
- Questions 1, 3, 5 have standard answers (see reference.md)
- Question 2 is planning-phase decision (not spec-phase)

**How to fix**:
- Fix classification: HAS_METRICS=true, HAS_DEPLOYMENT_IMPACT=true
- Add baseline: "Current: 95th percentile = 3.2s for 10k records"
- Add hypothesis: "Target: 95th percentile <500ms (10x improvement)"
- Use informed guesses: "Cache: Yes with 5-minute TTL", "Pagination: 20 results per page"
- Reduce clarifications to 1: "[NEEDS CLARIFICATION: Is full-text search required or exact match?]"

---

### Example 3: Add Email Notifications

**Feature**: "Send email notifications to users"

**Classification**:
- HAS_UI: maybe? (needs settings page?)
- IS_IMPROVEMENT: false
- HAS_METRICS: false
- HAS_DEPLOYMENT_IMPACT: maybe? (needs email service?)

**Spec Quality Issues**:
- ❌ **Unclear classification**: Ambiguous about UI needs
- ❌ **Unclear classification**: Deployment impact not assessed
- ❌ **8 clarifications**:
  1. [NEEDS CLARIFICATION: Which email service? SendGrid, AWS SES, Mailgun?]
  2. [NEEDS CLARIFICATION: Email templates needed?]
  3. [NEEDS CLARIFICATION: HTML or plain text?]
  4. [NEEDS CLARIFICATION: Unsubscribe functionality?]
  5. [NEEDS CLARIFICATION: Notification preferences UI?]
  6. [NEEDS CLARIFICATION: Rate limiting on emails?]
  7. [NEEDS CLARIFICATION: Retry logic for failed sends?]
  8. [NEEDS CLARIFICATION: Email delivery tracking?]
- ❌ No success criteria
- ❌ No user stories

**Why it's bad**:
- Classification is uncertain (UI needed for preferences? Deployment config for email service?)
- Questions 1, 3, 6, 7, 8 have standard answers (defer to plan, HTML+plain, yes, yes with backoff, optional)
- No user-facing success criteria (e.g., "User receives notification within 1 minute")
- Missing user stories (why do users need notifications?)

**How to fix**:
- Fix classification: HAS_UI=true (needs preferences page), HAS_DEPLOYMENT_IMPACT=true (email service creds)
- Use informed guesses: "HTML+plain text templates (accessibility)", "Retry: 3 attempts with exponential backoff"
- Reduce clarifications to 2 critical ones:
  1. "[NEEDS CLARIFICATION: Which events trigger notifications? (login, password reset, etc.)]"
  2. "[NEEDS CLARIFICATION: Should users opt-in or opt-out by default?]"
- Add success criteria: "User receives notification email within 1 minute of triggering event"
- Add user story: "As a user, I want to receive login alerts to detect unauthorized access"

---

## Side-by-Side Comparison

### Clarification Strategy

| Aspect | Good Spec | Bad Spec |
|--------|-----------|----------|
| **Clarifications** | ≤3 (only scope/security critical) | >5 (asks about everything) |
| **Technical defaults** | Uses informed guesses with docs | Asks questions with standard answers |
| **Format decisions** | Documents standard choice (JSON, CSV) | Asks user to choose format |
| **Performance** | Uses industry defaults (<500ms) | Asks user for target |
| **Rate limits** | Documents conservative default (100/min) | Asks user to specify |

### Success Criteria Quality

| Aspect | Good Spec | Bad Spec |
|--------|-----------|----------|
| **Measurability** | "User can login in <5 seconds" | "Login works correctly" |
| **Quantifiable** | "Process 100 files/hour" | "Process files quickly" |
| **User-facing** | "User receives email within 1 minute" | "Emails are sent" |
| **Performance** | "95th percentile <500ms" | "Search is fast" |
| **Accessibility** | "Lighthouse score ≥95" | "UI is accessible" |

### Classification Accuracy

| Aspect | Good Spec | Bad Spec |
|--------|-----------|----------|
| **UI detection** | Backend worker → HAS_UI=false ✓ | Background job → HAS_UI=true ✗ |
| **Improvement flag** | Performance optimization → IS_IMPROVEMENT=true ✓ | "Make faster" → IS_IMPROVEMENT=false ✗ |
| **Metrics flag** | User engagement feature → HAS_METRICS=true ✓ | Performance improvement → HAS_METRICS=false ✗ |
| **Deployment impact** | OAuth creds needed → HAS_DEPLOYMENT_IMPACT=true ✓ | Email service → HAS_DEPLOYMENT_IMPACT=maybe ✗ |

---

## Progressive Learning Pattern

As the specification-phase Skill captures more real-world examples:

1. **First 5 features**: Baseline patterns (track clarification count, classification accuracy)
2. **Features 6-15**: Refinement (identify common pitfalls, successful shortcuts)
3. **Features 16+**: Mastery (auto-detect edge cases, suggest improvements)

The Skill file updates automatically:
- Clarification count trends downward (target: ≤2 average)
- Classification accuracy trends upward (target: ≥90%)
- Time-to-spec trends downward (target: ≤15 minutes)
- Rework rate trends downward (target: <5% specs need revision)

**Example progression**:

| Metric | Features 1-5 | Features 6-15 | Features 16+ |
|--------|--------------|---------------|--------------|
| Avg clarifications | 4.2 | 2.8 | 1.5 |
| Classification accuracy | 80% | 88% | 94% |
| Time to spec | 22 min | 17 min | 12 min |
| Rework rate | 12% | 6% | 3% |

---

## Real-World Feature Examples

*This section will be populated as real features move through the workflow:*

### Feature: [Feature Name]

**Date**: YYYY-MM-DD
**Clarifications**: N
**Classification**: HAS_UI=X, IS_IMPROVEMENT=X, HAS_METRICS=X, HAS_DEPLOYMENT_IMPACT=X
**Time to spec**: N minutes
**Outcome**: ✅ Accepted | ⚠️ Reworked | ❌ Rejected

**Lessons learned**:
- [What went well]
- [What could improve]
- [Pattern to repeat]

---

_Examples updated as new features complete the specification phase._
