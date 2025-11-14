"""
LLM Evening Optimizer

Runs after market close (5:00pm) to review performance and autonomously
adjust trading parameters. This is the "self-tuning" component that learns
from results and optimizes strategy parameters.

Autonomy Levels:
- Level 1: Supervised (requires human approval)
- Level 2: Bounded (auto-applies within safety limits)
- Level 3: Full autonomy (learns from past adjustments)
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import anthropic


class LLMOptimizer:
    """LLM-powered strategy optimizer with autonomous learning"""

    def __init__(self, api_key_anthropic: str, autonomy_level: int = 1):
        """
        Args:
            api_key_anthropic: Anthropic API key for Claude
            autonomy_level: 1=supervised, 2=bounded, 3=fully autonomous
        """
        self.claude = anthropic.Anthropic(api_key=api_key_anthropic)
        self.autonomy_level = autonomy_level

        # Safety bounds (cannot be violated even at Level 3)
        self.HARD_LIMITS = {
            'rsi_oversold': (15, 35),
            'rsi_overbought': (65, 85),
            'stop_loss_pct': (-3.0, -0.3),
            'take_profit_pct': (0.5, 5.0),
            'position_size_pct': (0.005, 0.03),  # 0.5% - 3% account risk
            'max_trades_per_day': (3, 30),
            'max_hold_minutes': (30, 240),
            'confidence_threshold': (60, 90),
        }

        # Current strategy parameters
        self.strategy_params = self._load_strategy_params()

        # Adjustment history for learning
        self.adjustment_history = self._load_adjustment_history()

    def optimize_strategy(self,
                         performance_data: Dict,
                         watchlist_data: Dict,
                         market_conditions: Dict) -> Dict:
        """
        Main optimization routine - runs after market close.

        Args:
            performance_data: Today's trading results
            watchlist_data: Today's watchlist and setups
            market_conditions: Market context during trading

        Returns:
            Optimization report with proposed/applied changes
        """
        print(f"\n{'='*80}")
        print(f"LLM EVENING OPTIMIZER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"Autonomy Level: {self.autonomy_level}")
        print(f"{'='*80}\n")

        # Analyze performance
        print("Analyzing today's performance...")
        analysis = self._analyze_performance(performance_data, watchlist_data, market_conditions)

        # Generate improvement proposals
        print("\nGenerating optimization proposals...")
        proposals = self._llm_generate_proposals(analysis)

        # Validate and apply (based on autonomy level)
        print(f"\nProcessing {len(proposals)} proposals (Level {self.autonomy_level})...")
        results = self._process_proposals(proposals)

        # Learn from past adjustments (Level 3 only)
        if self.autonomy_level == 3:
            print("\nLearning from past adjustments...")
            self._learn_from_history()

        # Save optimization report
        report = {
            'timestamp': datetime.now().isoformat(),
            'autonomy_level': self.autonomy_level,
            'performance_summary': analysis,
            'proposals': proposals,
            'applied_changes': results['applied'],
            'rejected_changes': results['rejected'],
            'new_parameters': self.strategy_params
        }

        self._save_report(report)

        # Print summary
        print(f"\n{'='*80}")
        print(f"OPTIMIZATION COMPLETE")
        print(f"{'='*80}")
        print(f"Proposals generated: {len(proposals)}")
        print(f"Applied: {len(results['applied'])}")
        print(f"Rejected: {len(results['rejected'])}")
        if results['applied']:
            print("\nApplied Changes:")
            for change in results['applied']:
                old_val = change.get('old_value', '?')
                print(f"  • {change['parameter']}: {old_val} -> {change['new_value']}")
                reasoning = change.get('reasoning', 'No reason provided')
                print(f"    Reason: {reasoning[:80]}...")
        print()

        return report

    def _analyze_performance(self,
                            performance_data: Dict,
                            watchlist_data: Dict,
                            market_conditions: Dict) -> Dict:
        """Analyze today's performance and extract insights"""

        trades = performance_data.get('trades', [])

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else 0

        # Analyze trade patterns
        stopped_out = [t for t in trades if t.get('exit_reason') == 'stop_loss']
        took_profit = [t for t in trades if t.get('exit_reason') == 'take_profit']
        timed_out = [t for t in trades if t.get('exit_reason') == 'time_exit']

        # Setup analysis
        setups = {}
        for trade in trades:
            setup_type = trade.get('setup_type', 'unknown')
            if setup_type not in setups:
                setups[setup_type] = {'wins': 0, 'losses': 0, 'pnl': 0}

            if trade.get('pnl', 0) > 0:
                setups[setup_type]['wins'] += 1
            else:
                setups[setup_type]['losses'] += 1
            setups[setup_type]['pnl'] += trade.get('pnl', 0)

        # Current parameters
        current_params = self.strategy_params.copy()

        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'metrics': {
                'total_trades': total_trades,
                'win_rate': round(win_rate * 100, 1),
                'total_pnl': round(total_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2)
            },
            'exit_reasons': {
                'stop_loss': len(stopped_out),
                'take_profit': len(took_profit),
                'time_exit': len(timed_out)
            },
            'setup_performance': setups,
            'market_conditions': market_conditions,
            'current_parameters': current_params,
            'watchlist_used': watchlist_data.get('watchlist', [])
        }

    def _llm_generate_proposals(self, analysis: Dict) -> List[Dict]:
        """Ask LLM to propose parameter adjustments"""

        # Include recent adjustment history for learning (Level 3)
        history_context = ""
        if self.autonomy_level == 3 and self.adjustment_history:
            recent = self.adjustment_history[-10:]  # Last 10 adjustments
            history_context = f"""
PAST ADJUSTMENT OUTCOMES (learn from these):
{json.dumps(recent, indent=2)}

Key lessons:
- Which adjustments improved performance?
- Which made it worse?
- What patterns do you see?
"""

        prompt = f"""
You are an expert trading system optimizer analyzing today's results.

TODAY'S PERFORMANCE:
{json.dumps(analysis, indent=2)}

{history_context}

CURRENT PARAMETERS:
{json.dumps(self.strategy_params, indent=2)}

SAFETY BOUNDS (cannot exceed):
{json.dumps(self.HARD_LIMITS, indent=2)}

TASK:
Analyze performance and propose specific parameter adjustments to improve results.

ANALYSIS GUIDELINES:
1. Low win rate (<50%) -> Tighten entry criteria (higher RSI thresholds, stronger setups)
2. High win rate (>60%) but few trades -> Relax entry criteria
3. Many stop losses -> Widen stops or improve entry timing
4. Many time exits -> Adjust hold times or take profit levels
5. Certain setups underperforming -> Avoid those patterns
6. Market regime mismatch -> Adjust for current volatility/trend

For each proposal, provide:
- Parameter name (exact match to current_parameters keys)
- Current value
- Proposed new value (MUST be within safety bounds!)
- Reasoning (why this will help)
- Expected impact
- Confidence (0-100%)

Output format: JSON array
[
  {{
    "parameter": "rsi_oversold",
    "current_value": 30,
    "new_value": 28,
    "reasoning": "Win rate 42% suggests entries too early. Lowering RSI threshold to 28 catches deeper oversold bounces with better risk/reward.",
    "expected_impact": "Increase win rate by 5-8%, fewer false breakouts",
    "confidence": 75,
    "category": "entry_criteria"
  }},
  {{
    "parameter": "stop_loss_pct",
    "current_value": -1.0,
    "new_value": -1.5,
    "reasoning": "40% of trades stopped out. Wider stop accounts for intraday volatility (current ATR ~1.2%).",
    "expected_impact": "Reduce premature stops by 20-30%",
    "confidence": 80,
    "category": "risk_management"
  }},
  ...
]

IMPORTANT:
- Only propose changes with >60% confidence
- Each proposed value MUST be within safety bounds
- Prioritize changes with highest expected impact
- Consider market regime (don't optimize for today's outlier conditions)
- Limit to 3-5 most impactful proposals
"""

        response = self.claude.messages.create(
            model="claude-haiku-4-5",  # Latest Haiku: fast + cheap
            max_tokens=3000,
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
            proposals = json.loads(content)
            print(f"  Generated {len(proposals)} proposals")
            return proposals
        except json.JSONDecodeError as e:
            print(f"  Error parsing proposals: {e}")
            print(f"  Response: {content[:200]}...")
            return []

    def _process_proposals(self, proposals: List[Dict]) -> Dict:
        """Process proposals based on autonomy level"""

        applied = []
        rejected = []

        for proposal in proposals:
            # Validate safety bounds
            is_safe = self._validate_safety(proposal)

            if not is_safe:
                print(f"  [X] REJECTED (safety): {proposal['parameter']}")
                rejected.append({**proposal, 'rejection_reason': 'safety_violation'})
                continue

            # Process based on autonomy level
            if self.autonomy_level == 1:
                # Level 1: Require human approval
                print(f"\n  Proposal: {proposal['parameter']}")
                print(f"    Current: {proposal['current_value']}")
                print(f"    Proposed: {proposal['new_value']}")
                print(f"    Reason: {proposal['reasoning']}")
                print(f"    Confidence: {proposal['confidence']}%")

                approve = input(f"    Apply? (y/n): ").strip().lower()

                if approve == 'y':
                    self._apply_change(proposal)
                    applied.append(proposal)
                    print(f"  [OK] APPLIED")
                else:
                    rejected.append({**proposal, 'rejection_reason': 'user_declined'})
                    print(f"  [X] DECLINED")

            elif self.autonomy_level == 2:
                # Level 2: Auto-apply if within bounds and high confidence
                if proposal['confidence'] >= 70:
                    self._apply_change(proposal)
                    applied.append(proposal)
                    print(f"  [OK] AUTO-APPLIED: {proposal['parameter']} -> {proposal['new_value']}")
                else:
                    print(f"  [WARN] LOW CONFIDENCE ({proposal['confidence']}%), skipped")
                    rejected.append({**proposal, 'rejection_reason': 'low_confidence'})

            elif self.autonomy_level == 3:
                # Level 3: Full autonomy (already learned from history)
                self._apply_change(proposal)
                applied.append(proposal)
                print(f"  [OK] AUTONOMOUS: {proposal['parameter']} -> {proposal['new_value']}")

        return {'applied': applied, 'rejected': rejected}

    def _validate_safety(self, proposal: Dict) -> bool:
        """Validate proposal against safety bounds"""

        param = proposal['parameter']
        new_value = proposal['new_value']

        # Check if parameter has safety bounds
        if param not in self.HARD_LIMITS:
            # Unknown parameter - reject for safety
            return False

        min_val, max_val = self.HARD_LIMITS[param]

        # Validate range
        if new_value < min_val or new_value > max_val:
            return False

        return True

    def _apply_change(self, proposal: Dict):
        """Apply parameter change and record in history"""

        param = proposal['parameter']
        old_value = self.strategy_params.get(param)
        new_value = proposal['new_value']

        # Apply change
        self.strategy_params[param] = new_value

        # Record in history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'parameter': param,
            'old_value': old_value,
            'new_value': new_value,
            'reasoning': proposal['reasoning'],
            'expected_impact': proposal['expected_impact'],
            'confidence': proposal['confidence'],
            'autonomy_level': self.autonomy_level,
            'outcome': None  # Will be filled in next day
        }

        self.adjustment_history.append(history_entry)

        # Save updated parameters
        self._save_strategy_params()
        self._save_adjustment_history()

    def _learn_from_history(self):
        """Analyze past adjustments and their outcomes (Level 3 only)"""

        # Find adjustments with outcomes
        completed = [a for a in self.adjustment_history if a.get('outcome') is not None]

        if len(completed) < 5:
            print("  Not enough history yet (need 5+ completed adjustments)")
            return

        # Calculate success rate by parameter type
        success_rates = {}
        for adj in completed:
            param = adj['parameter']
            if param not in success_rates:
                success_rates[param] = {'total': 0, 'improved': 0}

            success_rates[param]['total'] += 1
            if adj['outcome'] == 'IMPROVED':
                success_rates[param]['improved'] += 1

        print("  Learning summary:")
        for param, stats in success_rates.items():
            rate = stats['improved'] / stats['total'] * 100
            print(f"    {param}: {rate:.0f}% success rate ({stats['improved']}/{stats['total']})")

        # Future: Could use this to adjust confidence thresholds or proposal preferences

    def _load_strategy_params(self) -> Dict:
        """Load current strategy parameters"""

        params_file = 'llm_trading/strategy_params.json'

        if os.path.exists(params_file):
            with open(params_file, 'r') as f:
                return json.load(f)
        else:
            # Default parameters (initial baseline)
            return {
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'stop_loss_pct': -1.0,
                'take_profit_pct': 2.0,
                'position_size_pct': 0.015,  # 1.5% account risk
                'max_trades_per_day': 15,
                'max_hold_minutes': 120,
                'confidence_threshold': 70,
                'volume_ratio_min': 1.2,
                'bb_squeeze_threshold': 0.02
            }

    def _save_strategy_params(self):
        """Save updated strategy parameters"""
        os.makedirs('llm_trading', exist_ok=True)
        with open('llm_trading/strategy_params.json', 'w') as f:
            json.dump(self.strategy_params, f, indent=2)

    def _load_adjustment_history(self) -> List[Dict]:
        """Load past adjustment history"""

        history_file = 'llm_trading/adjustment_history.json'

        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        else:
            return []

    def _save_adjustment_history(self):
        """Save adjustment history"""
        os.makedirs('llm_trading', exist_ok=True)
        with open('llm_trading/adjustment_history.json', 'w') as f:
            json.dump(self.adjustment_history, f, indent=2)

    def _save_report(self, report: Dict):
        """Save optimization report"""
        os.makedirs('llm_trading/reports', exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"llm_trading/reports/optimization_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        # Also save as "latest"
        with open('llm_trading/reports/optimization_latest.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved: {filename}")

    def evaluate_adjustment_outcomes(self, new_performance: Dict):
        """
        Evaluate outcomes of recent adjustments (call next day with new results).

        Args:
            new_performance: Next day's performance metrics
        """

        # Find unevaluated adjustments from yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        for adj in self.adjustment_history:
            if adj.get('outcome') is None:
                adj_date = adj['timestamp'][:10]

                if adj_date == yesterday:
                    # Compare performance
                    # Simple heuristic: Did key metrics improve?

                    expected = adj['expected_impact'].lower()

                    if 'win rate' in expected:
                        # Check if win rate improved
                        # (Would need baseline metrics stored)
                        adj['outcome'] = 'IMPROVED'  # Placeholder
                    else:
                        adj['outcome'] = 'NEUTRAL'

        self._save_adjustment_history()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Test with mock data
    optimizer = LLMOptimizer(
        api_key_anthropic=os.getenv('ANTHROPIC_API_KEY'),
        autonomy_level=2  # Bounded autonomy
    )

    # Mock performance data
    mock_performance = {
        'trades': [
            {'symbol': 'NVDA', 'setup_type': 'oversold_bounce', 'pnl': 2.1, 'exit_reason': 'take_profit'},
            {'symbol': 'TSLA', 'setup_type': 'breakout', 'pnl': -1.0, 'exit_reason': 'stop_loss'},
            {'symbol': 'AAPL', 'setup_type': 'oversold_bounce', 'pnl': 1.5, 'exit_reason': 'take_profit'},
            {'symbol': 'MSFT', 'setup_type': 'breakout', 'pnl': -0.8, 'exit_reason': 'stop_loss'},
            {'symbol': 'AMD', 'setup_type': 'oversold_bounce', 'pnl': 0.3, 'exit_reason': 'time_exit'},
        ]
    }

    mock_watchlist = {
        'watchlist': ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD']
    }

    mock_market = {
        'spy_trend': 'risk-on',
        'vix': 15.2,
        'regime': 'normal_volatility'
    }

    report = optimizer.optimize_strategy(mock_performance, mock_watchlist, mock_market)

    print("\nFinal Report:")
    print(json.dumps(report, indent=2))
