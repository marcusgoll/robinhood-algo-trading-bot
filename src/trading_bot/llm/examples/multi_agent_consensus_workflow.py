"""Multi-Agent Consensus Workflow Example.

Demonstrates how to use multiple agents to make collaborative trading decisions
with consensus voting (2/3 agents must agree).

Workflow:
1. RegimeDetectorAgent classifies current market regime
2. ResearchAgent analyzes fundamentals (FMP data)
3. NewsAnalystAgent checks sentiment from news
4. AgentOrchestrator runs consensus vote
5. RiskManagerAgent sizes position if consensus reached
6. Execute trade if approved

This example shows the full multi-agent decision process.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from trading_bot.llm.memory_service import AgentMemory
from trading_bot.llm.agents import (
    AgentOrchestrator,
    ResearchAgent,
    NewsAnalystAgent,
    RegimeDetectorAgent,
    RiskManagerAgent,
    TrendAnalystAgent,
    MomentumAnalystAgent,
    VolatilityAnalystAgent
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiAgentTradingWorkflow:
    """Orchestrates multi-agent collaborative trading decisions."""

    def __init__(self):
        """Initialize all agents with shared memory."""
        self.memory = AgentMemory()

        # Initialize orchestrator and regime detector (used for all assets)
        self.orchestrator = AgentOrchestrator(memory=self.memory)
        self.regime_detector = RegimeDetectorAgent(memory=self.memory)
        self.risk_manager = RiskManagerAgent(memory=self.memory)

        # Stock-focused agents (use fundamental + news data)
        self.research_agent = ResearchAgent(memory=self.memory)
        self.news_analyst = NewsAnalystAgent(memory=self.memory)

        # Crypto-focused agents (use technical analysis)
        self.trend_analyst = TrendAnalystAgent(memory=self.memory)
        self.momentum_analyst = MomentumAnalystAgent(memory=self.memory)
        self.volatility_analyst = VolatilityAnalystAgent(memory=self.memory)

        # Register all voting agents with orchestrator
        self.orchestrator.register_agent(self.research_agent)
        self.orchestrator.register_agent(self.news_analyst)
        self.orchestrator.register_agent(self.trend_analyst)
        self.orchestrator.register_agent(self.momentum_analyst)
        self.orchestrator.register_agent(self.volatility_analyst)
        self.orchestrator.register_agent(self.risk_manager)

        logger.info("Multi-agent workflow initialized - 6 voting agents registered (2 stock, 3 crypto, 1 risk)")

    def evaluate_trade_opportunity(
        self,
        symbol: str,
        current_price: float,
        portfolio_value: float,
        cash_available: float,
        technical_indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a trade opportunity using multi-agent consensus.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            current_price: Current stock price
            portfolio_value: Total portfolio value
            cash_available: Cash available for trading
            technical_indicators: Technical data (RSI, SMA, ATR, etc.)

        Returns:
            {
                'symbol': str,
                'decision': str,                    # BUY/HOLD/SKIP
                'consensus_reached': bool,
                'votes': List[dict],                # Agent votes
                'position_size_shares': int,        # If BUY
                'position_size_pct': float,         # If BUY
                'stop_loss_pct': float,            # If BUY
                'take_profit_pct': float,          # If BUY
                'summary': str,
                'total_cost_usd': float,
                'total_tokens': int
            }
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"EVALUATING TRADE OPPORTUNITY: {symbol} @ ${current_price}")
        logger.info(f"{'='*60}\n")

        total_cost = 0.0
        total_tokens = 0

        # Step 1: Detect market regime
        logger.info("Step 1: Detecting market regime...")
        regime_result = self.regime_detector.execute({
            'symbol': symbol,
            'current_price': current_price,
            'sma_20': technical_indicators.get('sma_20'),
            'sma_50': technical_indicators.get('sma_50'),
            'sma_200': technical_indicators.get('sma_200'),
            'atr': technical_indicators.get('atr'),
            'adx': technical_indicators.get('adx'),
            'volume_ratio': technical_indicators.get('volume_ratio')
        })

        total_cost += regime_result['cost_usd']
        total_tokens += regime_result['tokens_used']

        regime = regime_result['regime']
        regime_confidence = regime_result['confidence']

        logger.info(
            f"  Market Regime: {regime} "
            f"(confidence: {regime_confidence:.0f}%, "
            f"strength: {regime_result['regime_strength']})"
        )
        logger.info(f"  Key indicators: {', '.join(regime_result['key_indicators'])}")

        # Step 2: Run multi-agent consensus vote
        # Route to different agents based on asset type
        is_crypto = '/' in symbol  # Crypto symbols contain '/'

        if is_crypto:
            logger.info("\nStep 2: Running crypto technical analysis consensus (3 technical agents)...")
            agent_names = ['trend_analyst', 'momentum_analyst', 'volatility_analyst']
            min_agreement = 2  # 2 of 3 technical agents must agree for BUY
        else:
            logger.info("\nStep 2: Running stock fundamental analysis consensus (2 fundamental agents)...")
            agent_names = ['research', 'news_analyst']
            min_agreement = 2  # Both must agree for BUY

        # Build context for all voting agents
        consensus_context = {
            'symbol': symbol,
            'current_price': current_price,
            'technical_data': technical_indicators,
            'market_regime': regime,
            'regime_confidence': regime_confidence
        }

        # Use orchestrator for consensus
        consensus_result = self.orchestrator.multi_agent_consensus(
            agent_names=agent_names,
            context=consensus_context,
            min_agreement=min_agreement
        )

        total_cost += sum(vote.get('cost_usd', 0) for vote in consensus_result.get('votes', []))
        total_tokens += sum(vote.get('tokens_used', 0) for vote in consensus_result.get('votes', []))

        consensus_reached = consensus_result['consensus_reached']
        final_decision = consensus_result['decision']

        logger.info(f"\n  Consensus Result:")
        logger.info(f"    Decision: {final_decision}")
        logger.info(f"    Consensus Reached: {consensus_reached}")
        logger.info(f"    Agreement: {consensus_result['agreement_count']}/{len(consensus_result['votes'])}")
        logger.info(f"    Avg Confidence: {consensus_result['confidence_avg']:.1f}%")

        # Log individual votes
        logger.info(f"\n  Agent Votes:")
        for vote in consensus_result['votes']:
            logger.info(
                f"    {vote['agent_name']}: {vote['decision']} "
                f"(confidence: {vote['confidence']:.0f}%)"
            )
            logger.info(f"      Reasoning: {vote['reasoning']}")

        # Step 3: If consensus is BUY, get position sizing from RiskManager
        if consensus_reached and final_decision == 'BUY':
            logger.info(f"\n✅ CONSENSUS: BUY - {symbol} APPROVED BY AGENTS")
            logger.info(f"  Market Regime: {regime} ({regime_confidence:.0f}% confidence)")
            logger.info(f"  Agreement: {consensus_result['agreement_count']}/{len(consensus_result['votes'])} agents")
            logger.info(f"  Avg Confidence: {consensus_result['confidence_avg']:.1f}%")
            logger.info(f"  Why agents recommended BUY:")
            for vote in consensus_result['votes']:
                if vote['decision'] == 'BUY':
                    reasoning = vote['reasoning'][:150] + "..." if len(vote['reasoning']) > 150 else vote['reasoning']
                    logger.info(f"    • {vote['agent_name']}: {reasoning}")

            logger.info("\nStep 3: Calculating position size with RiskManager...")

            risk_result = self.risk_manager.execute({
                'symbol': symbol,
                'entry_price': current_price,
                'portfolio_value': portfolio_value,
                'cash_available': cash_available,
                'volatility': technical_indicators.get('atr'),
                'beta': technical_indicators.get('beta', 1.0),
                'market_regime': regime,
                'fundamental_score': max(
                    vote['confidence'] for vote in consensus_result['votes']
                    if vote['agent_name'] == 'research'
                )
            })

            total_cost += risk_result['cost_usd']
            total_tokens += risk_result['tokens_used']

            risk_decision = risk_result['decision']
            position_size_shares = risk_result['position_size_shares']
            position_size_pct = risk_result['position_size_pct']

            logger.info(f"\n  Risk Manager Decision: {risk_decision}")
            logger.info(f"    Position Size: {position_size_shares} shares ({position_size_pct:.1f}% of portfolio)")
            logger.info(f"    Stop Loss: {risk_result['stop_loss_pct']:.1f}% below entry")
            logger.info(f"    Take Profit: {risk_result['take_profit_pct']:.1f}% above entry")
            logger.info(f"    Risk/Reward: {risk_result['risk_reward_ratio']:.2f}")
            logger.info(f"    Kelly Size: {risk_result['kelly_size']:.1%}")

            # Final decision based on risk manager
            if risk_decision == 'APPROVE':
                final_action = 'BUY'
                summary = (
                    f"BUY {position_size_shares} shares of {symbol} @ ${current_price:.2f} "
                    f"(stop: {risk_result['stop_loss_pct']:.1f}%, "
                    f"target: {risk_result['take_profit_pct']:.1f}%)"
                )
            elif risk_decision == 'REDUCE':
                final_action = 'BUY'
                summary = (
                    f"BUY {position_size_shares} shares of {symbol} @ ${current_price:.2f} "
                    f"(REDUCED SIZE due to risk concerns)"
                )
            else:  # REJECT
                final_action = 'SKIP'
                summary = f"SKIP {symbol} - Risk manager rejected trade"
                position_size_shares = 0
                position_size_pct = 0.0

            return {
                'symbol': symbol,
                'decision': final_action,
                'consensus_reached': True,
                'votes': consensus_result['votes'],
                'position_size_shares': position_size_shares,
                'position_size_pct': position_size_pct,
                'stop_loss_pct': risk_result['stop_loss_pct'],
                'take_profit_pct': risk_result['take_profit_pct'],
                'risk_reward_ratio': risk_result['risk_reward_ratio'],
                'summary': summary,
                'total_cost_usd': total_cost,
                'total_tokens': total_tokens,
                'regime': regime,
                'regime_confidence': regime_confidence
            }

        else:
            # No consensus or decision is not BUY
            if not consensus_reached:
                # Log detailed reasoning why no consensus
                logger.info(f"\n❌ NO CONSENSUS - {symbol} SKIPPED")
                logger.info(f"  Market Regime: {regime} ({regime_confidence:.0f}% confidence)")
                logger.info(f"  Agent Votes Summary:")

                vote_summary = {}
                for vote in consensus_result['votes']:
                    decision = vote['decision']
                    vote_summary[decision] = vote_summary.get(decision, [])
                    vote_summary[decision].append(vote['agent_name'])

                for decision, agents in vote_summary.items():
                    logger.info(f"    {decision}: {', '.join(agents)}")

                # Log top reasoning from each vote
                logger.info(f"  Why agents skipped:")
                for vote in consensus_result['votes']:
                    reasoning = vote['reasoning'][:150] + "..." if len(vote['reasoning']) > 150 else vote['reasoning']
                    logger.info(f"    • {vote['agent_name']}: {reasoning}")

                summary = f"SKIP {symbol} - No consensus reached ({consensus_result['agreement_count']}/{len(consensus_result['votes'])} agents agreed)"
            else:
                # Consensus reached but decision was not BUY
                logger.info(f"\n⚠️  CONSENSUS: {final_decision} - {symbol} SKIPPED")
                logger.info(f"  Market Regime: {regime} ({regime_confidence:.0f}% confidence)")
                logger.info(f"  Agreement: {consensus_result['agreement_count']}/{len(consensus_result['votes'])} agents")
                logger.info(f"  Avg Confidence: {consensus_result['confidence_avg']:.1f}%")
                logger.info(f"  Why agents recommended {final_decision}:")
                for vote in consensus_result['votes']:
                    if vote['decision'] == final_decision:
                        reasoning = vote['reasoning'][:150] + "..." if len(vote['reasoning']) > 150 else vote['reasoning']
                        logger.info(f"    • {vote['agent_name']}: {reasoning}")

                summary = f"SKIP {symbol} - Consensus was {final_decision}"

            return {
                'symbol': symbol,
                'decision': 'SKIP',
                'consensus_reached': consensus_reached,
                'votes': consensus_result['votes'],
                'position_size_shares': 0,
                'position_size_pct': 0.0,
                'stop_loss_pct': 0.0,
                'take_profit_pct': 0.0,
                'risk_reward_ratio': 0.0,
                'summary': summary,
                'total_cost_usd': total_cost,
                'total_tokens': total_tokens,
                'regime': regime,
                'regime_confidence': regime_confidence
            }


def main():
    """Example usage of multi-agent consensus workflow."""

    # Initialize workflow
    workflow = MultiAgentTradingWorkflow()

    # Example trade opportunity
    symbol = "AAPL"
    current_price = 175.50
    portfolio_value = 100000.0
    cash_available = 50000.0

    # Example technical indicators (would come from market data in production)
    technical_indicators = {
        'sma_20': 172.30,
        'sma_50': 168.45,
        'sma_200': 165.20,
        'atr': 3.25,
        'adx': 28.5,
        'rsi': 58.2,
        'volume_ratio': 1.2,
        'beta': 1.15,
        'recent_high': 178.25,
        'recent_low': 170.15
    }

    # Evaluate trade
    result = workflow.evaluate_trade_opportunity(
        symbol=symbol,
        current_price=current_price,
        portfolio_value=portfolio_value,
        cash_available=cash_available,
        technical_indicators=technical_indicators
    )

    # Print final summary
    print("\n" + "="*60)
    print("FINAL DECISION")
    print("="*60)
    print(f"Symbol: {result['symbol']}")
    print(f"Decision: {result['decision']}")
    print(f"Consensus Reached: {result['consensus_reached']}")
    print(f"Market Regime: {result['regime']} ({result['regime_confidence']:.0f}%)")

    if result['decision'] == 'BUY':
        print(f"\nTRADE DETAILS:")
        print(f"  Shares: {result['position_size_shares']}")
        print(f"  Position Size: {result['position_size_pct']:.1f}% of portfolio")
        print(f"  Entry: ${current_price:.2f}")
        print(f"  Stop Loss: {result['stop_loss_pct']:.1f}% (${current_price * (1 - result['stop_loss_pct']/100):.2f})")
        print(f"  Take Profit: {result['take_profit_pct']:.1f}% (${current_price * (1 + result['take_profit_pct']/100):.2f})")
        print(f"  Risk/Reward: {result['risk_reward_ratio']:.2f}")

    print(f"\nSummary: {result['summary']}")
    print(f"\nCost: ${result['total_cost_usd']:.4f}")
    print(f"Tokens: {result['total_tokens']:,}")
    print("="*60)


if __name__ == "__main__":
    main()
