# Quickstart: 034-sentiment-analysis-integration

## Scenario 1: Initial Setup

```bash
# 1. Install new dependencies
cd D:/Coding/Stocks
pip install transformers==4.35.0 torch==2.1.0 tweepy==4.14.0 praw==7.7.1

# Or using requirements.txt
pip install -r requirements.txt

# 2. Configure API credentials (edit .env file)
cat >> .env <<EOF
# Sentiment Analysis API Credentials
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT="trading-bot:v1.0.0 (by /u/your_username)"
SENTIMENT_THRESHOLD=0.6
SENTIMENT_ENABLED=true
EOF

# 3. Download FinBERT model (runs automatically on first use, ~500MB download)
python -c "from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"

# 4. Create log file directory
mkdir -p logs

# 5. Test sentiment analysis module
python -m src.trading_bot.momentum.sentiment.sentiment_analyzer --symbol AAPL --dry-run
```

---

## Scenario 2: Validation

```bash
# 1. Run unit tests
pytest tests/unit/momentum/sentiment/ -v

# Example tests:
# - test_sentiment_fetcher_twitter.py - Twitter API integration
# - test_sentiment_fetcher_reddit.py - Reddit API integration
# - test_sentiment_analyzer.py - FinBERT model inference
# - test_sentiment_aggregator.py - 30-min rolling window aggregation
# - test_catalyst_detector_sentiment.py - CatalystDetector integration

# 2. Run integration tests
pytest tests/integration/momentum/sentiment/ -v

# Example tests:
# - test_sentiment_end_to_end.py - Full pipeline (fetch → analyze → aggregate)
# - test_catalyst_detector_with_sentiment.py - CatalystDetector.scan() with sentiment

# 3. Check test coverage
pytest --cov=src/trading_bot/momentum/sentiment --cov-report=term-missing

# Target: >80% coverage (constitution §Testing_Requirements)

# 4. Type checking
mypy src/trading_bot/momentum/sentiment/

# 5. Linting
ruff check src/trading_bot/momentum/sentiment/

# 6. Verify logs created
ls -lh logs/sentiment-analysis.jsonl
```

---

## Scenario 3: Manual Testing

### 3.1 Test Twitter API Integration
```python
# File: test_twitter_manual.py
import asyncio
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.sentiment.sentiment_fetcher import SentimentFetcher

async def test_twitter():
    config = MomentumConfig.from_env()
    fetcher = SentimentFetcher(config)

    # Fetch last 30 min of AAPL tweets
    posts = await fetcher.fetch_twitter_posts("AAPL", minutes=30)

    print(f"Found {len(posts)} Twitter posts for AAPL")
    for post in posts[:5]:  # Show first 5
        print(f"  @{post.author}: {post.text[:80]}...")
        print(f"  Posted: {post.timestamp}")

if __name__ == "__main__":
    asyncio.run(test_twitter())
```

Run:
```bash
python test_twitter_manual.py
```

Expected output:
```
Found 42 Twitter posts for AAPL
  @trader_123: AAPL crushing earnings, calls printing 🚀...
  Posted: 2025-10-29 14:25:00+00:00
  @investor_abc: Apple reports record Q4, beats on revenue and EPS...
  Posted: 2025-10-29 14:22:00+00:00
  ...
```

### 3.2 Test FinBERT Sentiment Analysis
```python
# File: test_finbert_manual.py
from src.trading_bot.momentum.sentiment.sentiment_analyzer import SentimentAnalyzer

def test_finbert():
    analyzer = SentimentAnalyzer()

    # Test bullish post
    bullish = "AAPL crushing earnings, calls printing 🚀"
    result = analyzer.analyze_post(bullish)
    print(f"Bullish post: {bullish}")
    print(f"  Negative: {result['negative']:.3f}")
    print(f"  Neutral:  {result['neutral']:.3f}")
    print(f"  Positive: {result['positive']:.3f}")
    print()

    # Test bearish post
    bearish = "TSLA production miss, might dump tomorrow"
    result = analyzer.analyze_post(bearish)
    print(f"Bearish post: {bearish}")
    print(f"  Negative: {result['negative']:.3f}")
    print(f"  Neutral:  {result['neutral']:.3f}")
    print(f"  Positive: {result['positive']:.3f}")

if __name__ == "__main__":
    test_finbert()
```

Run:
```bash
python test_finbert_manual.py
```

Expected output:
```
Bullish post: AAPL crushing earnings, calls printing 🚀
  Negative: 0.050
  Neutral:  0.100
  Positive: 0.850

Bearish post: TSLA production miss, might dump tomorrow
  Negative: 0.780
  Neutral:  0.150
  Positive: 0.070
```

### 3.3 Test Full Catalyst Detection with Sentiment
```python
# File: test_catalyst_sentiment_manual.py
import asyncio
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.catalyst_detector import CatalystDetector
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger

async def test_catalyst_with_sentiment():
    config = MomentumConfig.from_env()
    logger = MomentumLogger()
    detector = CatalystDetector(config, logger)

    # Scan for catalysts with sentiment
    symbols = ["AAPL", "TSLA", "NVDA"]
    signals = await detector.scan(symbols)

    print(f"Found {len(signals)} catalyst signals")
    for signal in signals:
        details = signal.details
        sentiment = details.get('sentiment_score', None)
        if sentiment is not None:
            print(f"{signal.symbol}: {details['headline'][:60]}...")
            print(f"  Catalyst: {details['catalyst_type']}")
            print(f"  Sentiment: {sentiment:.3f} ({'bullish' if sentiment > 0.6 else 'bearish' if sentiment < -0.6 else 'neutral'})")
        else:
            print(f"{signal.symbol}: {details['headline'][:60]}...")
            print(f"  Catalyst: {details['catalyst_type']}")
            print(f"  Sentiment: N/A (API unavailable or <10 posts)")

if __name__ == "__main__":
    asyncio.run(test_catalyst_with_sentiment())
```

Run:
```bash
python test_catalyst_sentiment_manual.py
```

Expected output:
```
Found 3 catalyst signals
AAPL: Apple reports record Q4 earnings, beats estimates...
  Catalyst: earnings
  Sentiment: 0.750 (bullish)
TSLA: Tesla production numbers miss analyst expectations...
  Catalyst: product
  Sentiment: -0.680 (bearish)
NVDA: Nvidia announces new AI chip, stock surges...
  Catalyst: product
  Sentiment: 0.820 (bullish)
```

### 3.4 Test Graceful Degradation (API Failure)
```bash
# Temporarily disable sentiment APIs
export SENTIMENT_ENABLED=false

# Run catalyst detector
python test_catalyst_sentiment_manual.py
```

Expected output:
```
Found 3 catalyst signals
AAPL: Apple reports record Q4 earnings, beats estimates...
  Catalyst: earnings
  Sentiment: N/A (sentiment disabled via SENTIMENT_ENABLED=false)
...
```

### 3.5 Check Logs
```bash
# View sentiment analysis logs
tail -f logs/sentiment-analysis.jsonl | jq .

# Example log entries:
# {"event": "sentiment.model_loaded", "timestamp": "2025-10-29T14:00:00Z", "model_name": "ProsusAI/finbert", "load_duration_ms": 1250, "memory_mb": 512}
# {"event": "sentiment.analysis_started", "timestamp": "2025-10-29T14:30:00Z", "symbol": "AAPL", "post_count": 42}
# {"event": "sentiment.analysis_completed", "timestamp": "2025-10-29T14:30:03Z", "symbol": "AAPL", "score": 0.75, "confidence": 0.85, "duration_ms": 2500}

# Query average sentiment for AAPL
grep '"symbol":"AAPL"' logs/sentiment-analysis.jsonl | \
  jq -r 'select(.event == "sentiment.analysis_completed") | .score' | \
  awk '{sum+=$1; count++} END {print "Average sentiment:", sum/count}'

# Check API error rate
total=$(grep '"event":"sentiment.analysis_started"' logs/sentiment-analysis.jsonl | wc -l)
errors=$(grep '"event":"sentiment.api_error"' logs/sentiment-analysis.jsonl | wc -l)
echo "API error rate: $(echo "scale=2; $errors / $total * 100" | bc)%"
```

---

## Scenario 4: Docker Deployment (VPS)

```bash
# 1. Update Docker image (add new dependencies)
cd /opt/trading-bot
git pull origin main

# 2. Rebuild Docker image (includes new dependencies)
docker-compose build trading-bot

# 3. Verify new dependencies installed
docker-compose run --rm trading-bot pip list | grep -E "(transformers|torch|tweepy|praw)"

# Expected output:
# praw                7.7.1
# torch               2.1.0
# transformers        4.35.0
# tweepy              4.14.0

# 4. Update .env with API credentials (see Scenario 1)
nano .env

# 5. Test FinBERT model download (inside container)
docker-compose run --rm trading-bot python -c "from transformers import AutoModelForSequenceClassification; AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"

# 6. Start bot (with sentiment analysis enabled)
docker-compose up -d trading-bot

# 7. Monitor logs
docker-compose logs -f trading-bot | grep -E "(sentiment|catalyst)"

# Expected output:
# trading-bot | INFO - FinBERT model loaded in 1.2s (512MB memory)
# trading-bot | INFO - Sentiment analysis enabled (Twitter + Reddit)
# trading-bot | INFO - CatalystDetector scan started for ['AAPL', 'TSLA', 'NVDA']
# trading-bot | INFO - Sentiment analysis completed for AAPL: score=0.75 (42 posts)
```

---

## Scenario 5: Rollback (Disable Sentiment)

```bash
# Quick rollback: Disable sentiment via environment variable (no code change)
# Edit .env:
SENTIMENT_ENABLED=false

# Restart bot
docker-compose restart trading-bot

# Verify sentiment disabled
docker-compose logs trading-bot | grep sentiment

# Expected output:
# trading-bot | WARNING - Sentiment analysis disabled via SENTIMENT_ENABLED=false
# trading-bot | INFO - CatalystDetector using news-only mode (no sentiment)
```

---

## Common Issues & Troubleshooting

### Issue 1: FinBERT model download fails
```bash
# Symptom: "ConnectionError: Failed to download model"
# Solution: Manual download with retry
pip install transformers torch
python -c "from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"
```

### Issue 2: Twitter API rate limit (429 error)
```bash
# Symptom: "RateLimitError: Twitter API rate limit exceeded"
# Solution: Check logs for rate limit tracking
grep '"event":"sentiment.api_error"' logs/sentiment-analysis.jsonl | jq -r 'select(.error_type == "rate_limit")'

# Wait 15 minutes, then retry (Twitter 15-min rate limit window)
```

### Issue 3: Sentiment analysis slow (>5s)
```bash
# Symptom: Analysis takes >5s per symbol
# Solution: Check if model is cached (should load once at startup)
grep '"event":"sentiment.model_loaded"' logs/sentiment-analysis.jsonl | tail -1

# If model loads multiple times, check for memory issues (model should stay in RAM)
```

### Issue 4: <10 posts found for symbol
```bash
# Symptom: "Insufficient posts for reliable sentiment (found 7, need 10)"
# Solution: Expected for low-volume symbols, gracefully degrades to sentiment_score=None
# Verify in logs:
grep '"post_count"' logs/sentiment-analysis.jsonl | jq -r 'select(.post_count < 10)'
```
