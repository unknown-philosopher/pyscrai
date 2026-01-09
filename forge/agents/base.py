"""
Base Agent Framework for Forge 3.0.

Defines the core Agent interface and common functionality.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.systems.llm.base import LLMProvider
    from forge.systems.llm.models import LLMMessage

logger = get_logger("agents.base")


# ============================================================================
# Agent Roles
# ============================================================================


class AgentRole(str, Enum):
    """Roles that agents can take on."""
    
    ANALYST = "analyst"         # Analyzes entities and relationships
    REVIEWER = "reviewer"       # Reviews extraction quality
    VALIDATOR = "validator"     # Validates data consistency
    NARRATOR = "narrator"       # Generates narrative summaries
    ADVISOR = "advisor"         # Provides strategic advice
    SCOUT = "scout"             # Searches for information


# ============================================================================
# Agent Response
# ============================================================================


@dataclass
class AgentResponse:
    """Response from an agent operation.
    
    Attributes:
        success: Whether the operation succeeded
        content: Main response content
        structured_data: Optional structured data (parsed JSON, etc.)
        confidence: Confidence score (0.0-1.0)
        reasoning: Agent's reasoning process
        sources: Source references used
        metadata: Additional metadata
        error: Error message if failed
    """
    
    success: bool
    content: str
    structured_data: dict | None = None
    confidence: float = 0.8
    reasoning: str = ""
    sources: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: str | None = None
    
    @property
    def failed(self) -> bool:
        return not self.success
    
    @classmethod
    def failure(cls, error: str) -> "AgentResponse":
        """Create a failure response."""
        return cls(
            success=False,
            content="",
            error=error,
            confidence=0.0,
        )
    
    @classmethod
    def from_content(
        cls,
        content: str,
        confidence: float = 0.8,
    ) -> "AgentResponse":
        """Create a success response from content."""
        return cls(
            success=True,
            content=content,
            confidence=confidence,
        )


# ============================================================================
# Base Agent
# ============================================================================


class Agent(ABC):
    """Base class for all Forge agents.
    
    Agents are specialized LLM-powered workers that perform
    specific analysis tasks. Each agent has:
    - A role defining its purpose
    - A system prompt defining its behavior
    - Access to the application state
    - Methods for specific operations
    
    Usage:
        class MyAgent(Agent):
            role = AgentRole.ANALYST
            
            def get_system_prompt(self) -> str:
                return "You are an analyst..."
            
            async def analyze(self, entity) -> AgentResponse:
                ...
    """
    
    role: AgentRole = AgentRole.ANALYST
    
    def __init__(
        self,
        state: "ForgeState",
        model: str | None = None,
        temperature: float = 0.7,
    ):
        """Initialize the agent.
        
        Args:
            state: Application state
            model: LLM model to use (default: from config)
            temperature: Generation temperature
        """
        self.state = state
        self.model = model or state.config.llm.model
        self.temperature = temperature
        self._conversation_history: list["LLMMessage"] = []
    
    @property
    def llm(self) -> "LLMProvider":
        """Get the LLM provider."""
        return self.state.llm
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.
        
        Returns:
            System prompt string
        """
        pass
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
    
    async def _generate(
        self,
        user_message: str,
        include_history: bool = False,
    ) -> str:
        """Generate a response from the LLM.
        
        Args:
            user_message: User message to send
            include_history: Whether to include conversation history
            
        Returns:
            Generated response content
        """
        from forge.systems.llm.models import LLMMessage
        
        messages = [
            LLMMessage(role="system", content=self.get_system_prompt()),
        ]
        
        if include_history:
            messages.extend(self._conversation_history)
        
        messages.append(LLMMessage(role="user", content=user_message))
        
        response = await self.llm.generate(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
        )
        
        # Store in history
        if include_history:
            self._conversation_history.append(
                LLMMessage(role="user", content=user_message)
            )
            self._conversation_history.append(
                LLMMessage(role="assistant", content=response.content)
            )
        
        return response.content
    
    async def _generate_structured(
        self,
        user_message: str,
        include_history: bool = False,
    ) -> AgentResponse:
        """Generate a structured response.
        
        Args:
            user_message: User message to send
            include_history: Whether to include conversation history
            
        Returns:
            AgentResponse with parsed content
        """
        import json
        
        try:
            content = await self._generate(user_message, include_history)
            
            # Try to extract JSON if present
            structured_data = None
            if "{" in content:
                try:
                    # Find JSON in response
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        structured_data = json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass
            
            return AgentResponse(
                success=True,
                content=content,
                structured_data=structured_data,
            )
            
        except Exception as e:
            logger.error(f"Agent generation failed: {e}")
            return AgentResponse.failure(str(e))
    
    def log(self, message: str, level: str = "info") -> None:
        """Log a message from this agent.
        
        Args:
            message: Message to log
            level: Log level
        """
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.role.value}] {message}")
