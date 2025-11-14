# Project Overview

**Last Updated**: 2025-10-26
**Status**: Active

## Vision Statement

The Robinhood Trading Bot is an automated momentum trading system designed to identify and execute high-probability trades based on premarket volume spikes, institutional catalyst detection, and bull flag pattern recognition. It exists because retail traders lack the tools and discipline to execute momentum strategies consistently—they miss the premarket window, hold losers too long, and trade emotionally. Our goal is to provide a disciplined, data-driven trading bot that automates the entire momentum trading workflow from signal detection to position sizing to profit-taking, while maintaining strict risk controls to prevent catastrophic losses.

**Problem**: Momentum trading requires constant market monitoring, split-second execution, and emotional discipline that few retail traders possess. Manual trading results in missed opportunities (premarket movers), poor entries (FOMO buys), and emotional exits (panic selling or greed-based holding).

**Solution**: A 24/7 automated trading bot that scans for momentum setups, validates them against technical patterns (bull flags, support/resistance), executes trades at optimal entry points, and manages positions with dynamic stop-loss adjustments and profit protection rules.

---

## Target Users

### Primary Persona: Active Retail Trader

**Who**: Individual day trader or swing trader, 6-24 months trading experience, has Robinhood account, trades $5K-$50K account size

**Example**: Alex, 28-year-old software engineer who trades part-time, manages $15K account, struggles to monitor markets during work hours (9am-5pm)

**Goals**:
- Automate premarket scanning to catch momentum movers before market open
- Execute trades with consistent discipline (no emotional decisions)
- Protect profits without constantly monitoring positions
- Improve win rate and reduce drawdowns vs manual trading

**Pain Points**:
- Misses premarket opportunities (at work 9-5, premarket is 4am-9:30am ET)
- Emotional trading: holds losers too long, sells winners too early
- Inconsistent strategy execution (FOMO trades, revenge trading)
- No systematic risk management (position sizing varies based on "feeling")

### Secondary Persona: Algorithm Trading Learner

**Who**: Aspiring algorithmic trader, technical background (programming), wants to learn systematic trading strategies

**Example**: Sarah, 24, CS graduate, wants to understand algorithmic trading before scaling capital

**Goals**:
- Learn momentum trading strategies through live bot operation
- Backtest strategies before risking real capital
- Understand risk management systems (circuit breakers, position sizing)
- Build foundation for eventually managing larger capital algorithmically

**Pain Points**:
- Lacks domain knowledge (trading) despite strong technical skills
- Risk-averse: wants paper trading mode before live trading
- Needs transparent, auditable system to understand what bot is doing
- Seeks educational value, not just profit

---

## Core Value Proposition

**For** active retail traders
**Who** want to trade momentum strategies but lack time/discipline to execute manually
**The** Robinhood Trading Bot
**Is an** automated day trading system
**That** scans for premarket movers, detects institutional catalysts, identifies bull flag patterns, and manages positions with dynamic risk controls
**Unlike** manual trading which is emotional and time-intensive
**Our product** executes 100% rule-based, emotionless trades 24/7 with systematic risk management

---

## Success Metrics

**Bot Performance KPIs** (how we measure trading success):

| Metric | Target | Timeframe | Measurement Source |
|--------|--------|-----------|-------------------|
| Win rate | >55% | Continuous (30-day rolling) | `logs/trades.jsonl` (completed trades) |
| Profit factor | >1.5 | Continuous (30-day rolling) | Total gains ÷ total losses |
| Max drawdown | <15% | Per trade, daily aggregate | Circuit breaker logs, position tracking |
| Sharpe ratio | >1.0 | Monthly | Risk-adjusted return calculation |
| Average R-multiple | >1.5R | Per trade | (Exit - Entry) ÷ Risk per trade |

**Operational KPIs** (system health):

| Metric | Target | Timeframe | Measurement Source |
|--------|--------|-----------|-------------------|
| Signal detection latency | <30s | Real-time | Premarket scanner logs |
| Order execution latency | <5s | Real-time | Robinhood API response times |
| System uptime | >99.5% | Monthly | Docker health checks, process monitoring |
| API error rate | <1% | Daily | Robinhood API error logs |

---

## Scope Boundaries

### In Scope (what we ARE building)

- **Momentum signal detection**: Premarket volume spikes, catalyst detection (news), bull flag patterns
- **Automated order execution**: Entry orders, stop-loss orders, profit-taking orders
- **Risk management**: Position sizing (% of portfolio), circuit breakers (daily loss limits, consecutive losses), emotional control (reduce size after losses)
- **Order flow monitoring**: Level 2 data analysis to detect institutional selling pressure
- **Performance tracking**: Trade logging, win rate, profit factor, drawdown tracking
- **LLM integration**: Natural language bot status queries, trade analysis
- **Backtesting**: Validate strategies against historical data before live trading
- **CLI dashboard**: Real-time monitoring of positions, performance, alerts

### Out of Scope (what we are NOT building)

- **Options trading** - **Why**: Complexity too high for MVP, focus on equities first
- **Crypto trading** - **Why**: Robinhood crypto API limited, requires separate risk model
- **Multi-account support** - **Why**: MVP targets solo trader (1 Robinhood account)
- **Mobile app** - **Why**: Bot runs headless 24/7, CLI dashboard sufficient for monitoring
- **Social features (copy trading, leaderboards)** - **Why**: Not a trading service, personal bot only
- **Broker-agnostic architecture** - **Why**: Robinhood API tightly coupled, porting to TD Ameritrade/Interactive Brokers deferred to v2.0
- **Advanced ML models** - **Why**: Rule-based strategies proven effective, ML adds complexity without clear ROI for MVP

---

## Competitive Landscape

### Direct Competitors

| Product | Strengths | Weaknesses | Price | Market Position |
|---------|-----------|------------|-------|----------------|
| Manual Trading (baseline) | Full control, no code | Time-intensive, emotional, requires constant monitoring | $0 | 100% of retail traders |
| TradingView Alerts + Manual | Excellent charting, alert flexibility | Still manual execution, no risk automation | $15-60/mo | Popular among technical traders |
| Proprietary trading bots (QuantConnect, etc.) | Professional-grade backtesting, multi-broker | Steep learning curve, expensive, overkill for small accounts | $20-200/mo | Institutional/serious retail |
| Commercial "signal" services | Curated trade ideas | Still manual execution, often low-quality signals | $50-500/mo | Retail traders seeking guidance |

### Our Positioning

**Positioning Statement**: "The Robinhood Trading Bot targets retail traders with $5K-$50K accounts who want systematic momentum trading without the complexity of professional-grade platforms. We're the fully automated, code-based solution between manual trading and expensive institutional platforms."

**Competitive Advantages**:
1. **Full automation**: Unlike TradingView alerts, executes trades automatically (no manual clicks)
2. **Open-source/self-hosted**: Unlike commercial bots, full code transparency + no monthly fees
3. **Momentum-specific**: Optimized for premarket movers + bull flags (not generic "works for everything")
4. **Risk-first design**: Circuit breakers, position sizing, emotional control built-in (not afterthought)

**Key Differentiators**:
- **Premarket scanning**: Most bots ignore 4am-9:30am window (where best opportunities emerge)
- **Catalyst detection**: Uses news sentiment + volume to filter fake breakouts
- **Order flow integration**: Polygon.io Level 2 data to detect institutional exits
- **Educational transparency**: Logs explain every decision (why trade rejected, why exited early)

---

## Project Timeline

**Phases**:

| Phase | Milestone | Target Date | Status |
|-------|-----------|-------------|--------|
| Phase 0 | Project design docs complete | 2025-10-26 | In progress |
| Phase 1 | Core trading loop (manual signals) | 2025-08-15 | Complete |
| Phase 2 | Automated signal detection (premarket scanner, bull flags) | 2025-09-30 | Complete |
| Phase 3 | Risk management (circuit breakers, position sizing) | 2025-10-15 | Complete |
| Phase 4 | Order flow monitoring (Polygon.io integration) | 2025-10-20 | Complete |
| Phase 5 | LLM integration (OpenAI API for analysis) | 2025-10-25 | Complete |
| Phase 6 | Production deployment (Docker, Hetzner VPS) | 2025-11-15 | Not started |
| Phase 7 | Live trading validation (paper trading 30 days) | 2025-12-15 | Not started |
| Phase 8 | Live trading (small capital $1K) | 2026-01-01 | Not started |

---

## Assumptions

**Critical assumptions** (if wrong, project strategy changes):

1. **Robinhood API stability** - **Validation**: Monitor API uptime >99%, track breaking changes
2. **Momentum strategies remain profitable in current market regime** - **Validation**: Backtest against last 6 months, paper trade 30 days before live
3. **Premarket volume spikes predict intraday continuation** - **Validation**: Backtest P(continuation | volume spike >200%) >60%
4. **$5K account size sufficient for meaningful profit** - **Validation**: Risk 1-2% per trade = $50-100 risk per trade, target 2R = $100-200 profit per win
5. **Polygon.io Level 2 data adds edge** - **Validation**: A/B test with/without order flow (expected: +5-10% win rate)
6. **Emotional control (reduce size after losses) improves performance** - **Validation**: Backtest with/without dynamic sizing, expect reduced max drawdown

---

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Robinhood API changes break bot | High | Medium | Comprehensive API error handling, fallback to manual mode, monitor Robinhood developer announcements |
| Market regime change (momentum stops working) | High | Low | Monthly strategy review, circuit breaker halts trading if win rate <45% over 50 trades |
| Broker restriction (pattern day trader rule) | Medium | Low | Use accounts >$25K, or limit to 3 day trades per week (swing trading mode) |
| Over-optimization (curve fitting to backtest) | High | Medium | Walk-forward validation, paper trade before live, avoid excessive parameter tuning |
| Catastrophic bug causing large loss | High | Low | Comprehensive testing, paper trading first, start with small capital ($1K), max loss per trade capped at 2% |
| Data feed outage (Alpaca, Polygon.io) | Medium | Medium | Graceful degradation: fallback to Yahoo Finance (free, lower quality), halt trading if no data |
| Server downtime (VPS outage) | Medium | Low | Hetzner >99.9% SLA, local backup server for critical monitoring |

---

## Team & Stakeholders

**Core Team**:
- Product/Engineering: Solo developer - System architecture, strategy implementation, deployment, monitoring

**Domain Advisors** (informal):
- Trading community (Reddit r/Daytrading, Discord servers) - Strategy validation, risk management feedback

**Stakeholders**:
- End user (self): Trading capital at risk, direct beneficiary of bot performance
- Robinhood: Broker providing execution infrastructure
- Data providers (Alpaca, Polygon.io): Market data feeds

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2025-10-26 | Initial project overview created | /init-project command executed |
| 2025-10-20 | Added order flow monitoring scope | Feature 028 shipped |
| 2025-10-15 | Added emotional control assumptions | Feature 027 shipped |
