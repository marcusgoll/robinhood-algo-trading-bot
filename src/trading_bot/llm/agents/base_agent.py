"""Base agent class that all specialized agents inherit from.

Provides:
- Automatic LLM call tracking in database
- Cost calculation for Claude API
- Standard interface (execute method)
- Memory integration for learning from past interactions
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID
import anthropic

from ..memory_service import AgentMemory


class BaseAgent(ABC):
    """Abstract base class for all trading agents.

    All agents must implement the execute() method which takes a context dict
    and returns results dict. The base class handles LLM calls, cost tracking,
    and memory storage automatically.
    """

    # Claude pricing (USD per million tokens) as of Jan 2025
    CLAUDE_HAIKU_4_5_INPUT_COST = 0.40
    CLAUDE_HAIKU_4_5_OUTPUT_COST = 2.00

    def __init__(
        self,
        agent_name: str,
        model: str = "claude-haiku-4-5",
        memory: Optional[AgentMemory] = None,
        api_key: Optional[str] = None
    ):
        """Initialize agent with name, model, and memory.

        Args:
            agent_name: Identifier for this agent (e.g., 'research', 'strategy_builder')
            model: Claude model to use (default: claude-haiku-4-5, latest as of Oct 2025)
            memory: AgentMemory instance (creates new if None)
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)
        """
        self.agent_name = agent_name
        self.model = model
        self.memory = memory or AgentMemory()

        # Initialize Anthropic client
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method that each agent must implement.

        Args:
            context: Input data for the agent (market data, symbols, etc.)

        Returns:
            Results dictionary with agent-specific output
        """
        pass

    def _call_llm(
        self,
        system_message: str,
        user_prompt: str,
        prompt_id: Optional[UUID] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Make LLM API call with automatic tracking.

        Wraps anthropic.messages.create() and stores:
        - Input context (system + user prompts)
        - Output result (text content)
        - Token usage
        - Cost in USD
        - Latency

        Args:
            system_message: System prompt defining agent role
            user_prompt: User message with specific task/data
            prompt_id: Reference to agent_prompts table (optional)
            max_tokens: Maximum output tokens
            temperature: Sampling temperature (0-1)
            **kwargs: Additional parameters for messages.create()

        Returns:
            {
                'content': str,           # LLM response text
                'tokens_used': int,       # Total tokens
                'cost_usd': float,        # Cost in USD
                'latency_ms': int,        # Response time
                'interaction_id': UUID    # Database record ID
            }
        """
        start_time = time.time()

        try:
            # Make API call
            response = self.client.messages.create(
                model=self.model,
                system=system_message,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Extract response content
            content = response.content[0].text if response.content else ""

            # Calculate metrics
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens

            cost_usd = self._calculate_cost(input_tokens, output_tokens)
            latency_ms = int((time.time() - start_time) * 1000)

            # Store in database
            interaction_id = self.memory.store_interaction(
                agent_name=self.agent_name,
                input_context={
                    "system": system_message,
                    "user": user_prompt,
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                output_result={
                    "content": content,
                    "stop_reason": response.stop_reason,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    }
                },
                model=self.model,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                prompt_id=prompt_id,
                success=True
            )

            return {
                "content": content,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "interaction_id": interaction_id
            }

        except Exception as e:
            # Log failed interaction
            latency_ms = int((time.time() - start_time) * 1000)

            interaction_id = self.memory.store_interaction(
                agent_name=self.agent_name,
                input_context={
                    "system": system_message,
                    "user": user_prompt,
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                output_result=None,
                model=self.model,
                tokens_used=None,
                cost_usd=None,
                latency_ms=latency_ms,
                prompt_id=prompt_id,
                success=False,
                error_message=str(e)
            )

            raise Exception(f"LLM call failed: {e}") from e

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for Claude API call.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.CLAUDE_HAIKU_4_5_INPUT_COST
        output_cost = (output_tokens / 1_000_000) * self.CLAUDE_HAIKU_4_5_OUTPUT_COST
        return input_cost + output_cost

    def __enter__(self):
        """Context manager entry (for memory session)."""
        self.memory.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (cleanup memory session)."""
        self.memory.__exit__(exc_type, exc_val, exc_tb)
