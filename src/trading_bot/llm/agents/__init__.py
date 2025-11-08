"""Multi-agent trading system with self-learning capabilities.

Agents:
- BaseAgent: Abstract class all agents inherit from
- AgentOrchestrator: Coordinates multiple agents and consensus voting
- ResearchAgent: FMP fundamental data enrichment
- RiskManagerAgent: Position sizing and risk assessment
- StrategyBuilderAgent: Strategy parameter optimization
- NewsAnalystAgent: Sentiment analysis from news
- RegimeDetectorAgent: Market regime classification
- LearningAgent: Self-improvement from trade outcomes
"""

from .base_agent import BaseAgent
from .orchestrator import AgentOrchestrator
from .research_agent import ResearchAgent
from .risk_manager_agent import RiskManagerAgent
from .strategy_builder_agent import StrategyBuilderAgent
from .news_analyst_agent import NewsAnalystAgent
from .regime_detector_agent import RegimeDetectorAgent
from .learning_agent import LearningAgent

__all__ = [
    "BaseAgent",
    "AgentOrchestrator",
    "ResearchAgent",
    "RiskManagerAgent",
    "StrategyBuilderAgent",
    "NewsAnalystAgent",
    "RegimeDetectorAgent",
    "LearningAgent"
]
