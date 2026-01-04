"""Human-in-the-Loop (HIL) protocol for interactive agent workflows.

This module defines the callback protocol that allows pausing agent pipelines
for human intervention, editing, approval, and feedback.
"""

from dataclasses import dataclass, asdict
from typing import Callable, Optional, Any, Literal
from enum import Enum


class HILAction(str, Enum):
    """Actions the user can take at a HIL pause point."""
    APPROVE = "approve"  # Continue with current results
    EDIT = "edit"  # Modify results
    RETRY = "retry"  # Rerun the agent with (optionally) modified prompt
    SKIP = "skip"  # Skip this phase
    ABORT = "abort"  # Cancel entire pipeline


@dataclass
class HILContext:
    """Context provided to the HIL callback at each pause point.
    
    This contains all information needed for the user to make decisions:
    - Which phase/agent is being paused
    - The prompt that was (or will be) used
    - The results produced (if post-execution)
    - Available actions
    """
    phase: str  # e.g., "scout", "analyst", "relationships", "validation"
    agent_name: str  # e.g., "ScoutAgent", "AnalystAgent"
    is_pre_execution: bool  # True if pausing before agent runs, False if after
    
    # Prompt information
    system_prompt: str = ""
    user_prompt: str = ""
    
    # Results (if post-execution)
    results: Any = None  # Could be list of entities, relationships, etc.
    
    # Metadata
    metadata: dict = None  # Additional context (e.g., entity count, validation errors)
    
    # Available actions at this point
    available_actions: list[HILAction] = None
    
    def __post_init__(self):
        if self.available_actions is None:
            if self.is_pre_execution:
                self.available_actions = [HILAction.APPROVE, HILAction.EDIT, HILAction.SKIP, HILAction.ABORT]
            else:
                self.available_actions = [HILAction.APPROVE, HILAction.EDIT, HILAction.RETRY, HILAction.SKIP, HILAction.ABORT]
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d['available_actions'] = [a.value for a in self.available_actions]
        return d


@dataclass
class HILResponse:
    """User's response to a HIL pause point."""
    action: HILAction
    
    # Modified data (if action is EDIT)
    edited_system_prompt: Optional[str] = None
    edited_user_prompt: Optional[str] = None
    edited_results: Any = None
    
    # User message/feedback
    message: str = ""


# HIL Callback Protocol
# The callback receives HILContext and returns HILResponse
HILCallback = Callable[[HILContext], HILResponse]


class HILManager:
    """Helper class to manage HIL callback execution.
    
    This wraps the callback with helpful utilities like:
    - Handling None callback (auto-approve)
    - Logging HIL interactions
    - Validating responses
    """
    
    def __init__(self, callback: Optional[HILCallback] = None, interactive: bool = True):
        """Initialize HIL manager.
        
        Args:
            callback: Function to call at each pause point
            interactive: If False, auto-approves all phases (non-interactive mode)
        """
        self.callback = callback
        self.interactive = interactive
        self.history: list[tuple[HILContext, HILResponse]] = []
        
    async def pause(self, context: HILContext) -> HILResponse:
        """Pause execution and wait for user response.
        
        Args:
            context: Information about current pause point
            
        Returns:
            User's response
        """
        # Non-interactive mode: auto-approve
        if not self.interactive or self.callback is None:
            response = HILResponse(action=HILAction.APPROVE)
            self.history.append((context, response))
            return response
        
        # Call user-provided callback
        try:
            response = await self.callback(context) if asyncio.iscoroutinefunction(self.callback) else self.callback(context)
            
            # Validate response
            if not isinstance(response, HILResponse):
                raise ValueError(f"HIL callback must return HILResponse, got {type(response)}")
            
            if response.action not in context.available_actions:
                raise ValueError(f"Action {response.action} not available at this point")
            
            self.history.append((context, response))
            return response
            
        except Exception as e:
            print(f"[HIL Error] {e}")
            # On error, abort to be safe
            return HILResponse(action=HILAction.ABORT, message=f"Error: {e}")
    
    def get_history(self) -> list[tuple[HILContext, HILResponse]]:
        """Get history of all HIL interactions."""
        return self.history
    
    def clear_history(self):
        """Clear HIL history."""
        self.history.clear()


import asyncio

__all__ = [
    "HILAction",
    "HILContext",
    "HILResponse",
    "HILCallback",
    "HILManager",
]
