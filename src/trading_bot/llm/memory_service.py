"""Agent memory service for PostgreSQL-backed long-term memory.

Provides high-level database operations for the multi-agent trading system:
- Store and retrieve LLM interactions
- Track strategy adjustments with outcomes
- Log trade outcomes for pattern learning
- Query similar market situations
- Store screener results
- Track agent performance metrics
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.dialects.postgresql import insert

# Import models (adjust path based on your structure)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'api'))

from app.models.agent_memory import (
    AgentPrompt, LLMInteraction, StrategyAdjustment,
    TradeOutcome, ScreenerResult, AgentMetric
)
from app.core.database import SessionLocal


class AgentMemory:
    """
    PostgreSQL-backed long-term memory for multi-agent trading system.

    Enables agents to:
    - Store every LLM call with cost/latency tracking
    - Link trades to the prompts that generated them
    - Learn from parameter adjustments (what worked/didn't)
    - Query similar past situations for pattern matching
    - Track performance over time

    Example:
        memory = AgentMemory()

        # Store LLM interaction
        interaction_id = memory.store_interaction(
            agent_name='research',
            prompt_id=prompt_uuid,
            input_context={'symbol': 'AAPL', 'price': 150.0},
            output_result={'thesis': 'bullish', 'confidence': 85},
            model='claude-haiku-4.5',
            tokens_used=500,
            cost_usd=0.0012
        )

        # Query similar situations
        similar = memory.get_similar_situations(
            current_context={'regime': 'BEAR', 'vix': 28},
            top_k=5
        )
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize memory service.

        Args:
            session: Optional SQLAlchemy session. If None, creates from SessionLocal.
        """
        self.session = session or SessionLocal()
        self._owns_session = session is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session:
            self.session.close()

    # ============ LLM INTERACTIONS ============

    def store_interaction(
        self,
        agent_name: str,
        input_context: Dict[str, Any],
        output_result: Optional[Dict[str, Any]],
        model: str,
        prompt_id: Optional[UUID] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        latency_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> UUID:
        """
        Store LLM interaction for cost tracking and learning.

        Args:
            agent_name: Which agent made the call
            input_context: Market data + prompt variables
            output_result: LLM's structured response
            model: Model identifier (e.g., 'claude-haiku-4.5')
            prompt_id: Optional link to prompt version used
            tokens_used: Total tokens consumed
            cost_usd: API call cost in USD
            latency_ms: Response time
            success: Whether call succeeded
            error_message: Error details if failed

        Returns:
            UUID of created interaction record
        """
        interaction = LLMInteraction(
            id=uuid4(),
            agent_name=agent_name,
            prompt_id=prompt_id,
            input_context=input_context,
            output_result=output_result,
            model=model,
            tokens_used=tokens_used,
            cost_usd=Decimal(str(cost_usd)) if cost_usd else None,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )

        self.session.add(interaction)
        self.session.commit()

        return interaction.id

    def get_interaction(self, interaction_id: UUID) -> Optional[LLMInteraction]:
        """Retrieve interaction by ID."""
        return self.session.query(LLMInteraction).filter(
            LLMInteraction.id == interaction_id
        ).first()

    def get_recent_interactions(
        self,
        agent_name: Optional[str] = None,
        limit: int = 100
    ) -> List[LLMInteraction]:
        """
        Get recent LLM interactions, optionally filtered by agent.

        Args:
            agent_name: Filter by agent (None = all agents)
            limit: Max interactions to return

        Returns:
            List of interactions, newest first
        """
        query = self.session.query(LLMInteraction)

        if agent_name:
            query = query.filter(LLMInteraction.agent_name == agent_name)

        return query.order_by(LLMInteraction.created_at.desc()).limit(limit).all()

    # ============ STRATEGY ADJUSTMENTS ============

    def store_adjustment(
        self,
        parameter_name: str,
        old_value: float,
        new_value: float,
        reasoning: str,
        proposed_by: str,
        confidence_score: float,
        expected_impact: Optional[str] = None
    ) -> UUID:
        """
        Store parameter adjustment proposal.

        Initially outcome is PENDING. Use update_adjustment_outcome()
        after measuring real-world results.

        Args:
            parameter_name: Parameter being adjusted (e.g., 'rsi_oversold')
            old_value: Current value
            new_value: Proposed new value
            reasoning: LLM's explanation
            proposed_by: Which agent proposed this
            confidence_score: LLM confidence (0-100)
            expected_impact: Predicted effect

        Returns:
            UUID of adjustment record
        """
        adjustment = StrategyAdjustment(
            id=uuid4(),
            parameter_name=parameter_name,
            old_value=Decimal(str(old_value)),
            new_value=Decimal(str(new_value)),
            reasoning=reasoning,
            expected_impact=expected_impact,
            confidence_score=Decimal(str(confidence_score)),
            proposed_by=proposed_by,
            outcome='PENDING'
        )

        self.session.add(adjustment)
        self.session.commit()

        return adjustment.id

    def update_adjustment_outcome(
        self,
        adjustment_id: UUID,
        outcome: str,  # 'IMPROVED', 'WORSENED', 'NEUTRAL'
        sharpe_before: Optional[float] = None,
        sharpe_after: Optional[float] = None,
        win_rate_before: Optional[float] = None,
        win_rate_after: Optional[float] = None
    ):
        """
        Update adjustment outcome after measuring real results.

        Args:
            adjustment_id: Adjustment to update
            outcome: Measured outcome ('IMPROVED', 'WORSENED', 'NEUTRAL')
            sharpe_before: Sharpe ratio before change
            sharpe_after: Sharpe ratio after change
            win_rate_before: Win rate before change
            win_rate_after: Win rate after change
        """
        adjustment = self.session.query(StrategyAdjustment).filter(
            StrategyAdjustment.id == adjustment_id
        ).first()

        if adjustment:
            adjustment.outcome = outcome
            adjustment.sharpe_before = Decimal(str(sharpe_before)) if sharpe_before else None
            adjustment.sharpe_after = Decimal(str(sharpe_after)) if sharpe_after else None
            adjustment.win_rate_before = Decimal(str(win_rate_before)) if win_rate_before else None
            adjustment.win_rate_after = Decimal(str(win_rate_after)) if win_rate_after else None
            adjustment.measured_at = datetime.now()

            self.session.commit()

    def get_adjustment_history(
        self,
        parameter_name: Optional[str] = None,
        limit: int = 20
    ) -> List[StrategyAdjustment]:
        """
        Get adjustment history, optionally filtered by parameter.

        Args:
            parameter_name: Filter by parameter (None = all)
            limit: Max adjustments to return

        Returns:
            List of adjustments, newest first
        """
        query = self.session.query(StrategyAdjustment)

        if parameter_name:
            query = query.filter(StrategyAdjustment.parameter_name == parameter_name)

        return query.order_by(StrategyAdjustment.created_at.desc()).limit(limit).all()

    def get_successful_adjustments(
        self,
        min_confidence: float = 70.0,
        limit: int = 10
    ) -> List[StrategyAdjustment]:
        """
        Get adjustments that improved performance.

        Useful for meta-learning: which types of adjustments work best?

        Args:
            min_confidence: Minimum confidence score
            limit: Max adjustments to return

        Returns:
            List of successful adjustments
        """
        return self.session.query(StrategyAdjustment).filter(
            and_(
                StrategyAdjustment.outcome == 'IMPROVED',
                StrategyAdjustment.confidence_score >= Decimal(str(min_confidence))
            )
        ).order_by(StrategyAdjustment.sharpe_after.desc()).limit(limit).all()

    # ============ TRADE OUTCOMES ============

    def store_trade_outcome(
        self,
        symbol: str,
        entry_time: datetime,
        exit_time: datetime,
        entry_price: float,
        exit_price: float,
        quantity: int,
        pnl: float,
        return_pct: float,
        setup_type: str,
        exit_reason: str,
        entry_reason: Optional[str] = None,
        market_regime: Optional[str] = None,
        vix_at_entry: Optional[float] = None,
        rsi_at_entry: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        llm_interaction_id: Optional[UUID] = None,
        strategy_params: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Store trade outcome for pattern learning.

        Links trade to the LLM interaction that generated the setup.

        Args:
            symbol: Ticker symbol
            entry_time: When entered
            exit_time: When exited
            entry_price: Entry price per share
            exit_price: Exit price per share
            quantity: Shares traded
            pnl: Profit/loss in dollars
            return_pct: Return percentage
            setup_type: Setup category (oversold_bounce, breakout, etc.)
            exit_reason: Why exited (stop_loss, take_profit, etc.)
            entry_reason: Why entered
            market_regime: Market regime at entry (BULL, BEAR, etc.)
            vix_at_entry: VIX value
            rsi_at_entry: RSI value
            volume_ratio: Volume vs average
            llm_interaction_id: Link to LLM call that generated trade
            strategy_params: Strategy parameters at trade time

        Returns:
            UUID of trade record
        """
        trade = TradeOutcome(
            id=uuid4(),
            symbol=symbol,
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=Decimal(str(entry_price)),
            exit_price=Decimal(str(exit_price)),
            quantity=quantity,
            pnl=Decimal(str(pnl)),
            return_pct=Decimal(str(return_pct)),
            setup_type=setup_type,
            entry_reason=entry_reason,
            exit_reason=exit_reason,
            market_regime=market_regime,
            vix_at_entry=Decimal(str(vix_at_entry)) if vix_at_entry else None,
            rsi_at_entry=Decimal(str(rsi_at_entry)) if rsi_at_entry else None,
            volume_ratio=Decimal(str(volume_ratio)) if volume_ratio else None,
            llm_interaction_id=llm_interaction_id,
            strategy_params=strategy_params
        )

        self.session.add(trade)
        self.session.commit()

        return trade.id

    def get_trades_by_setup(
        self,
        setup_type: str,
        market_regime: Optional[str] = None,
        limit: int = 100
    ) -> List[TradeOutcome]:
        """
        Query trades by setup type and optionally market regime.

        Useful for asking: "How well do oversold bounces work in bear markets?"

        Args:
            setup_type: Setup category to filter
            market_regime: Optional regime filter (BULL, BEAR, etc.)
            limit: Max trades to return

        Returns:
            List of matching trades
        """
        query = self.session.query(TradeOutcome).filter(
            TradeOutcome.setup_type == setup_type
        )

        if market_regime:
            query = query.filter(TradeOutcome.market_regime == market_regime)

        return query.order_by(TradeOutcome.created_at.desc()).limit(limit).all()

    def get_trade_performance_stats(
        self,
        setup_type: Optional[str] = None,
        market_regime: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate performance statistics for a setup/regime combination.

        Args:
            setup_type: Filter by setup (None = all)
            market_regime: Filter by regime (None = all)
            days_back: Look back period

        Returns:
            Dict with win_rate, avg_return, sharpe, etc.
        """
        cutoff = datetime.now() - timedelta(days=days_back)

        query = self.session.query(TradeOutcome).filter(
            TradeOutcome.created_at >= cutoff
        )

        if setup_type:
            query = query.filter(TradeOutcome.setup_type == setup_type)
        if market_regime:
            query = query.filter(TradeOutcome.market_regime == market_regime)

        trades = query.all()

        if not trades:
            return {'count': 0}

        returns = [float(t.return_pct) for t in trades]
        wins = sum(1 for r in returns if r > 0)

        return {
            'count': len(trades),
            'win_rate': (wins / len(trades)) * 100 if trades else 0,
            'avg_return': sum(returns) / len(returns) if returns else 0,
            'total_pnl': sum(float(t.pnl) for t in trades),
            'best_trade': max(returns) if returns else 0,
            'worst_trade': min(returns) if returns else 0
        }

    # ============ SCREENER RESULTS ============

    def store_screener_result(
        self,
        scan_id: UUID,
        symbol: str,
        filters_matched: Dict[str, Any],
        composite_score: float,
        asset_type: str = 'stock',
        fundamental_snapshot: Optional[Dict[str, Any]] = None,
        technical_snapshot: Optional[Dict[str, Any]] = None,
        selected_for_watchlist: bool = False
    ) -> UUID:
        """
        Store screener result for forward-looking outcome tracking.

        Args:
            scan_id: UUID grouping this scan batch
            symbol: Symbol identified
            filters_matched: Which filters passed
            composite_score: Opportunity score (0-100)
            asset_type: Asset type (stock, crypto, etf)
            fundamental_snapshot: FMP data
            technical_snapshot: Technical indicators
            selected_for_watchlist: Whether added to watchlist

        Returns:
            UUID of screener result
        """
        result = ScreenerResult(
            id=uuid4(),
            scan_id=scan_id,
            symbol=symbol,
            asset_type=asset_type,
            filters_matched=filters_matched,
            fundamental_snapshot=fundamental_snapshot,
            technical_snapshot=technical_snapshot,
            composite_score=Decimal(str(composite_score)),
            selected_for_watchlist=selected_for_watchlist
        )

        self.session.add(result)
        self.session.commit()

        return result.id

    def update_screener_outcomes(
        self,
        scan_id: UUID,
        outcomes_7d: Dict[str, float],
        outcomes_30d: Optional[Dict[str, float]] = None
    ):
        """
        Update forward-looking outcomes for a scan batch.

        Args:
            scan_id: Scan to update
            outcomes_7d: Dict mapping symbol -> 7-day return %
            outcomes_30d: Optional 30-day returns
        """
        results = self.session.query(ScreenerResult).filter(
            ScreenerResult.scan_id == scan_id
        ).all()

        for result in results:
            if result.symbol in outcomes_7d:
                result.outcome_7d = Decimal(str(outcomes_7d[result.symbol]))

            if outcomes_30d and result.symbol in outcomes_30d:
                result.outcome_30d = Decimal(str(outcomes_30d[result.symbol]))

        self.session.commit()

    # ============ AGENT METRICS ============

    def store_agent_metrics(
        self,
        agent_name: str,
        date: date,
        tasks_completed: int,
        avg_latency_ms: Optional[int] = None,
        success_rate: Optional[float] = None,
        avg_confidence: Optional[float] = None,
        impact_on_pnl: Optional[float] = None,
        cost_usd: float = 0.0
    ):
        """
        Store or update agent metrics for a given day.

        Uses upsert to handle multiple updates same day.

        Args:
            agent_name: Agent being measured
            date: Date of metrics
            tasks_completed: Number of tasks
            avg_latency_ms: Average latency
            success_rate: Success rate %
            avg_confidence: Average confidence
            impact_on_pnl: Downstream P&L impact
            cost_usd: Total API cost
        """
        # Upsert using PostgreSQL's ON CONFLICT
        stmt = insert(AgentMetric).values(
            id=uuid4(),
            agent_name=agent_name,
            date=date,
            tasks_completed=tasks_completed,
            avg_latency_ms=avg_latency_ms,
            success_rate=Decimal(str(success_rate)) if success_rate else None,
            avg_confidence=Decimal(str(avg_confidence)) if avg_confidence else None,
            impact_on_pnl=Decimal(str(impact_on_pnl)) if impact_on_pnl else None,
            cost_usd=Decimal(str(cost_usd))
        ).on_conflict_do_update(
            index_elements=['agent_name', 'date'],
            set_={
                'tasks_completed': stmt.excluded.tasks_completed,
                'avg_latency_ms': stmt.excluded.avg_latency_ms,
                'success_rate': stmt.excluded.success_rate,
                'avg_confidence': stmt.excluded.avg_confidence,
                'impact_on_pnl': stmt.excluded.impact_on_pnl,
                'cost_usd': stmt.excluded.cost_usd
            }
        )

        self.session.execute(stmt)
        self.session.commit()

    def get_agent_metrics(
        self,
        agent_name: Optional[str] = None,
        days_back: int = 30
    ) -> List[AgentMetric]:
        """
        Get agent metrics for analysis.

        Args:
            agent_name: Filter by agent (None = all)
            days_back: Look back period

        Returns:
            List of agent metrics
        """
        cutoff = date.today() - timedelta(days=days_back)

        query = self.session.query(AgentMetric).filter(
            AgentMetric.date >= cutoff
        )

        if agent_name:
            query = query.filter(AgentMetric.agent_name == agent_name)

        return query.order_by(AgentMetric.date.desc()).all()
