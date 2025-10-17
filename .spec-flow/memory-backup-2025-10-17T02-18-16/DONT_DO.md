# Don't Do This

Anti-patterns and failures discovered during development.

---

## 2025-10-07: Trading Without Circuit Breakers

**Context**: Constitution v1.0.0
**Reason**: Financial bots must have hard limits to prevent catastrophic losses

Never deploy a trading bot without:
- Maximum daily loss limit
- Maximum trades per day
- Position size limits
- Emergency stop mechanism

## 2025-10-07: Hard-Coded API Credentials

**Context**: Constitution v1.0.0
**Reason**: Security vulnerability and accidental exposure risk

Never:
- Store credentials in code
- Commit `.env` files with real secrets
- Use plaintext API keys

Always:
- Use environment variables
- Use secret management (e.g., Doppler, AWS Secrets Manager)
- Add `.env` to `.gitignore`

## 2025-10-07: Skipping Paper Trading

**Context**: Constitution v1.0.0
**Reason**: Real money trades require validation

Never deploy directly to production. Always:
1. Unit test all logic
2. Backtest against historical data
3. Paper trade in live market conditions
4. Monitor for at least 1 week
5. Only then consider real money

## 2025-10-07: Ignoring API Rate Limits

**Context**: Constitution v1.0.0
**Reason**: Robinhood will ban accounts that abuse API

Never:
- Make unlimited API calls
- Ignore 429 rate limit errors
- Retry immediately on failure

Always:
- Implement exponential backoff
- Track request counts
- Respect documented limits
- Cache responses when possible
