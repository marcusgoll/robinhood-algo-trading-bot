# Error Log: Sentiment Analysis Integration

## Planning Phase (Phase 0-2)
None yet.

## Implementation Phase (Phase 3-4)
[Populated during /tasks and /implement]

## Testing Phase (Phase 5)
[Populated during /debug and /preview]

## Deployment Phase (Phase 6-7)
[Populated during staging validation and production deployment]

---

## Error Template

**Error ID**: ERR-[NNN]
**Phase**: [Planning/Implementation/Testing/Deployment]
**Date**: YYYY-MM-DD HH:MM
**Component**: [sentiment_fetcher/sentiment_analyzer/sentiment_aggregator/catalyst_detector/deployment]
**Severity**: [Critical/High/Medium/Low]

**Description**:
[What happened]

**Root Cause**:
[Why it happened]

**Resolution**:
[How it was fixed]

**Prevention**:
[How to prevent in future]

**Related**:
- Spec: [link to requirement]
- Code: [file:line]
- Commit: [sha]

---

## Common Error Patterns (Anticipated)

### ERR-SENT-001: FinBERT Model Download Failure
**Anticipated Issue**: ConnectionError during model download (ProsusAI/finbert from Hugging Face Hub)
**Symptom**: Bot startup fails with "Failed to download model" error
**Resolution**:
1. Check internet connectivity on VPS
2. Manually download model: `python -c "from transformers import AutoModelForSequenceClassification; AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"`
3. If persistent, pre-download model in Docker build step
**Prevention**: Add model download to Docker build process (cache in image)

### ERR-SENT-002: Twitter API Rate Limit (429 Error)
**Anticipated Issue**: RateLimitError when exceeding Twitter API free tier (500k tweets/month)
**Symptom**: "sentiment.api_error" event logged with error_type="rate_limit"
**Resolution**:
1. Graceful degradation: sentiment_score=None, bot continues with news-only
2. Wait 15 minutes (Twitter rate limit window resets)
3. Monitor API usage: `grep rate_limit logs/sentiment-analysis.jsonl | wc -l`
**Prevention**: Track monthly API usage, alert at 80% quota (400k tweets)

### ERR-SENT-003: Reddit API Authentication Failure
**Anticipated Issue**: AuthenticationError due to invalid REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET
**Symptom**: "sentiment.api_error" event logged with error_type="auth_failed", source="Reddit"
**Resolution**:
1. Verify .env credentials: `grep REDDIT_ .env`
2. Test Reddit auth: `python -c "import praw; r = praw.Reddit(...); print(r.user.me())"`
3. Regenerate Reddit API credentials if expired
**Prevention**: Add startup validation for API credentials (test auth before first scan)

### ERR-SENT-004: Insufficient Posts for Reliable Sentiment (<10 posts)
**Anticipated Issue**: Low-volume symbols have <10 posts in last 30 minutes
**Symptom**: "Insufficient posts for reliable sentiment (found 7, need 10)" warning in logs
**Resolution**:
1. Expected behavior: Graceful degradation, sentiment_score=None
2. No action needed (US4 requirement: min 10 posts for reliable signal)
**Prevention**: Not preventable (low-volume symbols expected), document in spec

### ERR-SENT-005: FinBERT Inference Timeout (>5s)
**Anticipated Issue**: Model inference takes >5s for batch of 50 posts (violates NFR-001 <3s)
**Symptom**: "duration_ms" >5000 in sentiment.analysis_completed logs
**Resolution**:
1. Check VPS memory: `free -m` (FinBERT requires 1GB RAM)
2. Reduce batch size: Analyze 25 posts at a time instead of 50
3. Skip sentiment if inference takes >5s (graceful degradation)
**Prevention**: Monitor P95 latency, alert if >3s

### ERR-SENT-006: Docker Image Too Large (>5GB)
**Anticipated Issue**: Docker image exceeds VPS disk space (20GB total)
**Symptom**: `docker-compose build` fails with "no space left on device"
**Resolution**:
1. Clean Docker cache: `docker system prune -a`
2. Optimize with multi-stage Docker build (build deps in separate stage)
3. Use slimmer PyTorch distribution (torch-cpu instead of torch-cuda)
**Prevention**: Monitor disk usage: `df -h`, alert if >15GB used

### ERR-SENT-007: Sentiment Score Out of Range
**Anticipated Issue**: Aggregated sentiment_score >1.0 or <-1.0 (validation error)
**Symptom**: ValueError in CatalystEvent.__post_init__()
**Resolution**:
1. Debug aggregation logic: Check weighted average calculation
2. Verify FinBERT outputs sum to 1.0 (probabilities)
3. Clamp score to [-1.0, 1.0] range before CatalystEvent creation
**Prevention**: Add unit test for edge cases (all positive, all negative, mixed sentiment)

### ERR-SENT-008: Feature Flag Not Respected
**Anticipated Issue**: Sentiment analysis runs even when SENTIMENT_ENABLED=false
**Symptom**: sentiment_score populated in logs despite feature flag disabled
**Resolution**:
1. Check .env file: `grep SENTIMENT_ENABLED .env`
2. Restart bot to reload environment: `docker-compose restart trading-bot`
3. Add startup log: "Sentiment analysis enabled/disabled" for verification
**Prevention**: Add unit test for feature flag check in CatalystDetector.scan()
