"""
LLM Morning Screener

Uses Claude to analyze market context and generate daily watchlist.
Runs once before market open (9:00am).
"""

import os
import json
from datetime import datetime
from typing import List, Dict
import anthropic
from .market_context import MarketContextBuilder


class LLMScreener:
    """LLM-powered morning watchlist generator"""

    def __init__(self, api_key_alpaca: str, api_secret_alpaca: str, api_key_anthropic: str):
        self.context_builder = MarketContextBuilder(api_key_alpaca, api_secret_alpaca)
        self.claude = anthropic.Anthropic(api_key=api_key_anthropic)

    def generate_watchlist(self, candidate_symbols: List[str], max_picks: int = 15) -> List[Dict]:
        """
        Generate daily watchlist from candidate symbols.

        Args:
            candidate_symbols: Pool of symbols to analyze (e.g., top 100 by volume)
            max_picks: Maximum number of stocks to watch today

        Returns:
            List of watchlist entries with trade setups
        """
        print(f"\n{'='*80}")
        print(f"LLM MORNING SCREENER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*80}\n")

        # Build context for each candidate
        print(f"Analyzing {len(candidate_symbols)} candidates...")
        contexts = {}
        for symbol in candidate_symbols:
            print(f"  {symbol}...", end=" ", flush=True)
            context = self.context_builder.build_full_context(symbol)
            if 'error' not in context:
                contexts[symbol] = context
                print("[OK]")
            else:
                print(f"[FAIL] ({context['error']})")

        print(f"\nSuccessfully analyzed {len(contexts)} symbols")

        # Ask LLM to select best opportunities
        watchlist = self._llm_select_opportunities(contexts, max_picks)

        # Generate trade setups for selected symbols
        final_watchlist = []
        for entry in watchlist:
            symbol = entry['symbol']
            setup = self._llm_generate_trade_setup(symbol, contexts[symbol], entry['reasoning'])
            final_watchlist.append(setup)

        # Save watchlist
        self._save_watchlist(final_watchlist)

        print(f"\n{'='*80}")
        print(f"WATCHLIST GENERATED: {len(final_watchlist)} stocks")
        print(f"{'='*80}\n")

        for i, entry in enumerate(final_watchlist, 1):
            print(f"{i}. {entry['symbol']} - {entry['setup_type']}")
            print(f"   Catalyst: {entry['catalyst']}")
            print(f"   Confidence: {entry['confidence']}%")
            print()

        return final_watchlist

    def _llm_select_opportunities(self, contexts: Dict[str, Dict], max_picks: int) -> List[Dict]:
        """Ask LLM to select best opportunities from candidates"""

        # Build summary for each symbol (full context too long)
        summaries = {}
        for symbol, context in contexts.items():
            summaries[symbol] = {
                'price': context['price_action']['current_price'],
                'change_pct': context['price_action']['change_pct'],
                'rsi': context['technicals']['rsi_14']['value'],
                'rsi_level': context['technicals']['rsi_14']['level'],
                'volume_ratio': context['volume']['ratio'],
                'trend': context['price_action']['trend_short_term'],
                'bb_position': context['technicals']['bollinger_bands']['interpretation'],
                'market_sentiment': context['market_context']['market_sentiment']
            }

        prompt = f"""
You are an expert day trader selecting stocks for today's watchlist.

MARKET OVERVIEW:
- Date: {datetime.now().strftime('%Y-%m-%d')}
- Overall market: {contexts[next(iter(contexts))]['market_context']['spy_trend']}
- Regime: {contexts[next(iter(contexts))]['market_context']['regime']}

CANDIDATE STOCKS:
{json.dumps(summaries, indent=2)}

TASK:
Select the TOP {max_picks} stocks with the best risk/reward setups for TODAY.

CRITERIA (prioritize):
1. Clear technical setup (oversold bounce, breakout, etc.)
2. Strong catalyst (volume spike, near support/resistance)
3. Alignment with market trend
4. Good risk/reward (clear entry/exit)
5. Liquid (high volume ratio)

For each selected stock, provide:
- Symbol
- Setup type (e.g., "oversold bounce", "breakout", "pullback to support")
- Primary catalyst (what makes it interesting TODAY)
- Confidence (0-100%)
- Reasoning (2-3 sentences)

Output format: JSON array
[
  {{
    "symbol": "NVDA",
    "setup_type": "oversold bounce",
    "catalyst": "RSI 28 + touching lower BB + high volume",
    "confidence": 75,
    "reasoning": "Strong oversold signal with technical support. Volume spike suggests institutional interest. Market risk-on supports tech bounce."
  }},
  ...
]

IMPORTANT:
- Only include stocks with >60% confidence
- Prioritize setups with clear entry/exit
- Consider market regime (avoid longs in strong downtrend)
- Ensure liquidity (volume ratio >1.0)
"""

        response = self.claude.messages.create(
            model="claude-haiku-4-5",  # Latest Haiku: fast + cheap
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        content = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            watchlist = json.loads(content)
            return watchlist[:max_picks]  # Ensure we don't exceed max
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response: {content}")
            return []

    def _llm_generate_trade_setup(self, symbol: str, context: Dict, reasoning: str) -> Dict:
        """Generate detailed trade setup with entry/exit criteria"""

        prompt = f"""
You are an expert day trader creating a trade plan for {symbol}.

FULL MARKET CONTEXT:
{json.dumps(context, indent=2)}

INITIAL ANALYSIS:
{reasoning}

TASK:
Create a detailed intraday trade setup with specific rules for automated execution.

Provide:
1. Entry criteria (when to enter)
   - Price level or condition
   - Confirmation signals
   - Time constraints (e.g., "only before 11am")

2. Exit criteria
   - Take profit target (% or price level)
   - Stop loss (% or price level)
   - Time-based exit (max hold time)

3. Position sizing guidance
   - Risk level (low/medium/high)
   - Suggested account risk (0.5% - 2%)

4. Invalidation (when setup is no longer valid)

Output format: JSON
{{
  "symbol": "{symbol}",
  "setup_type": "...",
  "catalyst": "...",
  "confidence": 75,
  "entry": {{
    "condition": "price breaks above 145.50 with volume",
    "confirmation": "RSI stays above 30",
    "time_window": "9:30am - 11:30am"
  }},
  "exit": {{
    "take_profit_pct": 2.0,
    "take_profit_price": 148.40,
    "stop_loss_pct": -1.0,
    "stop_loss_price": 144.00,
    "max_hold_minutes": 120,
    "time_exit": "3:50pm (before close)"
  }},
  "risk": {{
    "level": "medium",
    "account_risk_pct": 1.5,
    "rationale": "Clear technical setup with defined risk"
  }},
  "invalidation": "If breaks below 143.50 or RSI fails to hold 30",
  "reasoning": "{reasoning}"
}}

IMPORTANT:
- Be specific with price levels and percentages
- Risk/reward should be at least 1.5:1
- Stop loss max -2%
- Take profit max +5%
- Account for intraday volatility
"""

        response = self.claude.messages.create(
            model="claude-haiku-4-5",  # Latest Haiku: fast + cheap
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        content = response.content[0].text

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            setup = json.loads(content)
            return setup
        except json.JSONDecodeError as e:
            print(f"Error parsing setup for {symbol}: {e}")
            # Return minimal setup
            return {
                "symbol": symbol,
                "setup_type": "undefined",
                "catalyst": reasoning,
                "confidence": 50,
                "entry": {"condition": "manual review required"},
                "exit": {"take_profit_pct": 2.0, "stop_loss_pct": -1.0},
                "risk": {"level": "medium", "account_risk_pct": 1.0},
                "invalidation": "manual review",
                "reasoning": reasoning
            }

    def _save_watchlist(self, watchlist: List[Dict]):
        """Save watchlist to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"watchlists/watchlist_{timestamp}.json"

        os.makedirs("watchlists", exist_ok=True)

        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'watchlist': watchlist
            }, f, indent=2)

        # Also save as "latest" for easy access
        with open("watchlists/watchlist_latest.json", 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'watchlist': watchlist
            }, f, indent=2)

        print(f"\nWatchlist saved: {filename}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    screener = LLMScreener(
        api_key_alpaca=os.getenv('ALPACA_API_KEY'),
        api_secret_alpaca=os.getenv('ALPACA_SECRET_KEY'),
        api_key_anthropic=os.getenv('ANTHROPIC_API_KEY')
    )

    # Test with a few high-volume stocks
    candidates = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'AMD']

    watchlist = screener.generate_watchlist(candidates, max_picks=5)

    print("\nFinal Watchlist:")
    for i, entry in enumerate(watchlist, 1):
        print(f"\n{i}. {entry['symbol']} ({entry['confidence']}% confidence)")
        print(f"   Setup: {entry['setup_type']}")

        # Handle different entry formats
        entry_condition = entry.get('entry', {})
        if isinstance(entry_condition, dict):
            entry_text = entry_condition.get('condition') or entry_condition.get('primary_condition') or str(entry_condition)
        else:
            entry_text = str(entry_condition)
        print(f"   Entry: {entry_text}")

        # Handle different exit formats (may have nested structures) - try multiple paths
        exit_info = entry.get('exit', {})

        # Try to extract take profit
        tp_found = False
        for key_path in [
            'take_profit_pct',
            ('take_profit_primary', 'pct'),
            ('take_profit_primary', 'price'),
            ('upside_scenario', 'take_profit_pct'),
            ('take_profit_targets', 0, 'pct_1'),
            'long_take_profit_pct'
        ]:
            if tp_found:
                break
            if isinstance(key_path, tuple):
                val = exit_info
                for k in key_path:
                    if isinstance(val, dict) and k in val:
                        val = val[k]
                    elif isinstance(val, list) and isinstance(k, int) and len(val) > k:
                        val = val[k]
                    else:
                        val = None
                        break
                if val is not None:
                    print(f"   Target: +{val}%" if isinstance(val, (int, float)) else f"   Target: {val}")
                    tp_found = True
            elif key_path in exit_info:
                print(f"   Target: +{exit_info[key_path]}%")
                tp_found = True

        # Try to extract stop loss
        sl_found = False
        for key_path in [
            'stop_loss_pct',
            ('stop_loss', 'pct'),
            ('stop_loss', 'price'),
            ('upside_scenario', 'stop_loss_pct'),
            'stop_loss_pct_long'
        ]:
            if sl_found:
                break
            if isinstance(key_path, tuple):
                val = exit_info
                for k in key_path:
                    if isinstance(val, dict) and k in val:
                        val = val[k]
                    else:
                        val = None
                        break
                if val is not None:
                    print(f"   Stop: {val}%" if isinstance(val, (int, float)) else f"   Stop: {val}")
                    sl_found = True
            elif key_path in exit_info:
                print(f"   Stop: {exit_info[key_path]}%")
                sl_found = True
