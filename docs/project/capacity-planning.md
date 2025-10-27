# Capacity Planning

**Last Updated**: 2025-10-26
**Related Docs**: See `system-architecture.md` for components, `tech-stack.md` for infrastructure choices

## Current Scale (MVP Baseline)

**Users**: 1 (solo trader)
**Accounts**: 1 Robinhood account
**Trades**: 10-50 trades/day (momentum strategy)
**Positions**: <10 concurrent positions
**API Calls**: <1,000/day (Robinhood + Alpaca + Polygon)
**Storage**: <1GB (mostly trade logs)
**Budget**: $130-150/mo total

**Cost Breakdown**:
- Hetzner VPS (CX11): $11/mo (2GB RAM, 1 vCPU, 40GB SSD)
- Polygon.io (Starter): $99/mo (Level 2 data, 5 symbols concurrent)
- OpenAI (GPT-4o-mini): $20-40/mo (pattern analysis, ~$0.15/1K tokens)
- Domain/DNS: $12/year (~$1/mo)
- **Total**: ~$131-151/mo

**Constraints**:
- Single VPS instance (no redundancy)
- Single Docker Compose deployment
- File-based logs (no database scalability)
- Robinhood API rate limits (60 req/min)
- Polygon.io concurrent symbol limit (5 symbols)

---

## Growth Projections

### Tier 1: Multi-Account (1 → 5 accounts)

**Timeline**: 6-12 months (if expanding to friends/family)
**Triggers**:
- Manual deployment becomes tedious (need automation)
- Want to test multiple strategies simultaneously
- Logs directory > 5GB (file system strain)

**Infrastructure Changes**:

| Component | Current | New | Cost Change |
|-----------|---------|-----|-------------|
| VPS | CX11 (2GB RAM, 1 vCPU) | CX21 (4GB RAM, 2 vCPU) | +$6/mo |
| Polygon.io | Starter (5 symbols) | Developer ($199/mo, 100 symbols) | +$100/mo |
| OpenAI | $20-40/mo | $50-80/mo (5x usage) | +$30-40/mo |
| Storage | 40GB SSD | 80GB SSD | +$5/mo |

**Total New Cost**: $131/mo → $267/mo (+$136/mo, +103%)

**Capacity**:
- 5 concurrent bot instances (1 per account)
- 50-250 trades/day (5x increase)
- 5,000 API calls/day
- 5GB storage (5x logs)

**Implementation**:
```yaml
# docker-compose.yml (multi-account)
services:
  trading-bot-account-1:
    ...
    env_file: .env.account1
  trading-bot-account-2:
    ...
    env_file: .env.account2
  # ... up to 5 accounts
```

**Bottlenecks**:
- Polygon.io symbol limit (100 symbols enough for 5 accounts)
- VPS CPU (2 vCPU shared among 5 bots)
- Manual management (no orchestration)

---

### Tier 2: Automated Platform (5 → 20 accounts)

**Timeline**: 18-24 months (if building SaaS product)
**Triggers**:
- Manual VPS management unsustainable
- Need database for analytics (file-based too slow)
- Want web dashboard (not just CLI)

**Infrastructure Changes**:

| Component | Tier 1 | Tier 2 | Cost Change |
|-----------|--------|--------|-------------|
| VPS | 1x CX21 (4GB) | 3x CX21 (load balanced) | +$12/mo |
| Database | None (file-based) | Managed PostgreSQL (10GB) | +$30/mo |
| Load Balancer | None | Hetzner Load Balancer | +$6/mo |
| Monitoring | Logs only | Prometheus + Grafana (self-hosted) | +$0 |
| Storage | 80GB SSD | 160GB SSD | +$10/mo |
| Polygon.io | Developer ($199/mo) | Professional ($399/mo, 500 symbols) | +$200/mo |
| OpenAI | $50-80/mo | $100-150/mo (20x usage) | +$50-70/mo |

**Total New Cost**: $267/mo → $575/mo (+$308/mo, +115%)

**Capacity**:
- 20 concurrent bot instances
- 200-1,000 trades/day
- 20,000 API calls/day
- 50GB storage (database + logs)

**Architecture Changes**:
- **Database**: Migrate from JSONL to PostgreSQL (trade logs, performance metrics)
- **Load Balancing**: Distribute API requests across 3 VPS instances
- **Web Dashboard**: React frontend + FastAPI backend (replace CLI dashboard)
- **Monitoring**: Prometheus scrapes bot metrics, Grafana visualizes

**Bottlenecks**:
- PostgreSQL single instance (no replication)
- Polygon.io symbol limit (500 symbols enough for 20 accounts)
- Manual deployment (still docker-compose, no CI/CD)

---

### Tier 3: SaaS Product (20 → 100+ accounts)

**Timeline**: 3-5 years (if successful product)
**Triggers**:
- Revenue > $5,000/mo (justifies infrastructure investment)
- Need multi-tenancy (customer separation)
- Regulatory requirements (audit logs, data retention)

**Infrastructure Changes**:

| Component | Tier 2 | Tier 3 | Cost Change |
|-----------|--------|--------|-------------|
| VPS | 3x CX21 | 10x CX31 (8GB RAM, 4 vCPU) | +$100/mo |
| Database | PostgreSQL 10GB | PostgreSQL 100GB (HA, 2 replicas) | +$100/mo |
| Cache | Redis (single) | Redis Cluster (3 nodes) | +$30/mo |
| CDN | None | Cloudflare Pro | +$20/mo |
| Monitoring | Self-hosted | Datadog APM | +$100/mo |
| CI/CD | Manual | GitHub Actions (paid) | +$20/mo |
| Storage | 160GB SSD | 500GB SSD | +$30/mo |
| Polygon.io | Professional ($399/mo) | Enterprise (custom pricing, ~$1,000/mo) | +$601/mo |
| OpenAI | $100-150/mo | $500-1,000/mo (100x usage) | +$400-850/mo |

**Total New Cost**: $575/mo → $2,976/mo (+$2,401/mo, +417%)

**Capacity**:
- 100 concurrent bot instances
- 1,000-5,000 trades/day
- 100,000 API calls/day
- 500GB storage
- Multi-region deployment (US-East, US-West)

**Architecture Changes**:
- **Microservices**: Split into scanner, executor, monitor services
- **Message Queue**: RabbitMQ for order distribution
- **Multi-Tenancy**: PostgreSQL schemas per customer
- **CI/CD**: Automated testing + deployment pipeline
- **Observability**: Distributed tracing (OpenTelemetry)

**Bottlenecks**:
- Robinhood API rate limits (60 req/min per account, hard limit)
- Database write throughput (need sharding if >10K trades/day)
- Cost optimization becomes critical (engineering time on cost reduction)

---

## Resource Estimates

### Compute (Bot Process)

**Current**:
- 1 bot instance: ~200MB RAM, 0.2 vCPU
- Handles 10-50 trades/day (low throughput)

**Formula**: RAM per bot = base (100MB) + market data cache (50MB) + log buffer (50MB)

**Example Calculation**:
- Tier 1 (5 bots): 5 × 200MB = 1GB RAM used (out of 4GB available)
- Tier 2 (20 bots): 20 × 200MB = 4GB RAM → need 3x VPS (spread 7 bots per VPS)

### API Call Budget

**Current**: <1,000 calls/day
- Robinhood: ~200 calls/day (orders + position checks)
- Alpaca: ~500 calls/day (market data, 1-minute bars)
- Polygon.io: WebSocket (continuous), ~100 REST calls/day
- OpenAI: ~20 calls/day (pattern analysis, cached)

**Formula**: Total calls/day = (accounts × trades/day × 10 calls/trade) + (accounts × 500 market data calls)

**Example**:
- 1 account: (1 × 30 × 10) + 500 = 800 calls/day
- 5 accounts: (5 × 30 × 10) + 2,500 = 4,000 calls/day
- 20 accounts: (20 × 30 × 10) + 10,000 = 16,000 calls/day

**Rate Limit Headroom**:
- Robinhood: 60 req/min = 86,400 req/day (well above needs)
- Alpaca: 200 req/min = 288,000 req/day (plenty of headroom)

### Storage

**Current**: <1GB

**Formula**: Total storage = (trades/day × 1KB/trade × 90 days) + (logs × 3 rotations × 10MB)

**Example**:
- 30 trades/day: (30 × 1KB × 90) = 2.7MB trade logs + 30MB app logs = ~50MB
- 1 year: ~200MB (trades) + 365MB (app logs) = ~565MB total

**Growth Rate**: ~50MB/month per account

---

## Cost Model

### Cost Per Trade

**Tier 0 (Current)**:
- Total cost: $131/mo
- Trades: 30/day × 22 trading days = 660 trades/mo
- **Cost per trade**: $0.20/trade

**Tier 1 (5 accounts)**:
- Total cost: $267/mo
- Trades: 150/day × 22 = 3,300 trades/mo
- **Cost per trade**: $0.08/trade (60% reduction due to economies of scale)

**Tier 2 (20 accounts)**:
- Total cost: $575/mo
- Trades: 600/day × 22 = 13,200 trades/mo
- **Cost per trade**: $0.044/trade (78% reduction)

**Economics**: Cost per trade decreases as scale increases (shared infrastructure costs)

### Revenue Targets (If SaaS)

**Pricing Model** (hypothetical): $49/mo per account

**Break-Even**:
- Tier 1 ($267/mo cost): 6 paying accounts
- Tier 2 ($575/mo cost): 12 paying accounts
- Tier 3 ($2,976/mo cost): 61 paying accounts

**Healthy Margin** (5x cost coverage):
- Tier 1: 30 accounts → $1,470/mo revenue, $267 cost = 82% margin
- Tier 2: 60 accounts → $2,940/mo revenue, $575 cost = 80% margin
- Tier 3: 305 accounts → $14,945/mo revenue, $2,976 cost = 80% margin

---

## Performance Targets by Tier

| Metric | Tier 0 (1 acct) | Tier 1 (5 accts) | Tier 2 (20 accts) | Tier 3 (100 accts) |
|--------|-----------------|------------------|-------------------|-------------------|
| Order execution time | < 2s | < 2s | < 1s | < 500ms |
| API response time p95 | < 500ms | < 500ms | < 300ms | < 200ms |
| Log write latency | < 10ms | < 10ms | < 5ms (DB) | < 5ms (DB) |
| Dashboard refresh | 5s | 5s | 2s | 1s (web) |
| Uptime | 99% | 99.5% | 99.9% | 99.99% |
| Max concurrent positions | 10 | 50 | 200 | 1,000 |

---

## Scaling Triggers

**When to Scale**: Proactive scaling based on thresholds

| Trigger | Action | Lead Time |
|---------|--------|-----------|
| RAM > 80% for 1 hour | Upgrade VPS tier or add VPS | 1 day |
| CPU > 70% for 30 min | Optimize code or scale horizontally | 1 week |
| Storage > 80% capacity | Increase SSD size | 3 days |
| Trade logs > 100K records | Migrate to PostgreSQL | 2 weeks |
| API errors > 2% (rate limit) | Reduce polling frequency or upgrade API tier | 1 day |

**Auto-Scaling**: Not implemented (manual VPS scaling)
**Future**: Kubernetes auto-scaling based on CPU/RAM metrics

---

## Disaster Scenarios

### Scenario 1: VPS Failure (Hardware/Network)

**Cause**: Hetzner VPS outage (rare, but possible)
**Impact**:
- All trading stops (single VPS, no redundancy)
- No access to bot (CLI dashboard down)
- Trade logs safe (backed up daily)

**Response**:
1. **Immediate** (0-15 min): Check Hetzner status page
2. **Short-term** (15-60 min): Spin up backup VPS, restore from backup
3. **Long-term** (1-3 days): Review post-mortem, add VPS redundancy

**Cost**: +$11/mo for standby VPS (cold standby, only start if primary fails)

### Scenario 2: Polygon.io Outage (Level 2 Data Loss)

**Impact**: Order flow monitoring unavailable (worse exit timing)

**Response**:
1. **Immediate**: Log warning, continue trading without L2 data
2. **Degraded Mode**: Use L1 data only (Alpaca quotes)
3. **Recovery**: Reconnect when Polygon.io recovers

**Cost**: $0 (graceful degradation)

### Scenario 3: Robinhood API Rate Limit Exceeded

**Impact**: Cannot place orders (trading halted)

**Response**:
1. **Immediate**: Queue orders in memory
2. **Retry**: Exponential backoff (wait 1s, 2s, 4s, ...)
3. **Alert**: Log CRITICAL if queue > 10 orders

**Cost**: $0 (retry logic)

---

## Optimization Opportunities

### Current (Tier 0) Optimizations

**Low-hanging fruit** (implement now):
1. **LLM caching**: Redis cache for pattern analysis (+90% cache hit rate, save $30/mo)
2. **Log compression**: Gzip old logs (-50% storage)
3. **API polling reduction**: Cache quotes for 5s instead of polling every 1s (-80% Alpaca calls)

**ROI**: High (minimal cost, significant savings)

### Tier 1 Optimizations

**As we grow**:
1. **Database migration**: Move from JSONL to SQLite (+10x query speed)
2. **Multi-threading**: Parallel bot instances (-30% CPU usage)
3. **CDN for dashboard**: Cloudflare (if building web UI)

**ROI**: Medium (some cost, good performance gain)

### Tier 2+ Optimizations

**At scale**:
1. **Database sharding**: Partition by account_id (+10x write throughput)
2. **Read replicas**: Offload analytics queries (+50% read capacity)
3. **Message queue**: Async order processing (+70% throughput)

**ROI**: Medium (higher cost, necessary for scale)

---

## Breaking Points

**What fails first at each tier:**

**Tier 0 → Tier 1**:
- **First to break**: VPS RAM (running 5 bots on 2GB)
- **Symptom**: OOM errors, bot crashes
- **Fix**: Upgrade to CX21 (4GB) (+$6/mo)

**Tier 1 → Tier 2**:
- **First to break**: File-based logs (grep too slow for >10K records)
- **Symptom**: Dashboard lag, slow queries
- **Fix**: Migrate to PostgreSQL (+$30/mo)

**Tier 2 → Tier 3**:
- **First to break**: Single PostgreSQL instance (write throughput)
- **Symptom**: Slow writes (> 500ms), replication lag
- **Fix**: Sharding + read replicas (+$100/mo)

---

## Monitoring & Alerts

**Metrics to Track**:

| Metric | Tool | Alert Threshold |
|--------|------|----------------|
| VPS RAM usage | Hetzner dashboard | > 80% for 1 hour |
| VPS CPU usage | Hetzner dashboard | > 70% for 30 min |
| Disk usage | df command | > 80% capacity |
| Log file size | ls -lh | > 100MB per file |
| API error rate | Bot logs | > 2% errors |
| Trade execution time | Bot logs | > 2s for 10 trades |
| Monthly cost | Billing dashboard | > $200 (Tier 0) |

**Alert Channels**:
- Critical (VPS down): Email (Hetzner alerts)
- Warning (high usage): Bot logs (review weekly)

---

## Change Log

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2025-10-26 | Initial capacity planning | Document scaling roadmap | Foundation for growth |
| 2025-10-01 | Added OpenAI budget tracking | Control LLM costs | Alert at $80/mo (80% of budget) |
| 2025-09-20 | Upgraded to CX11 VPS | More headroom for growth | +$5/mo, 2GB → 4GB RAM (later downgraded to CX11) |
| 2025-09-15 | Added Polygon.io | Level 2 data for better exits | +$99/mo |
