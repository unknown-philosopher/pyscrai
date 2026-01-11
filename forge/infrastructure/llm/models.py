"""
Data models for LLM interactions in Forge 3.0.

Defines message types, conversation containers, and model information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


# ============================================================================
# Message Types
# ============================================================================


class MessageRole(str, Enum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class LLMMessage:
    """A single chat message."""
    
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    model: str | None = None
    tokens_used: int | None = None
    
    def to_api_format(self) -> dict[str, str]:
        """Convert to OpenAI-compatible API format."""
        return {
            "role": self.role.value,
            "content": self.content,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "tokens_used": self.tokens_used,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMMessage":
        """Create from dictionary."""
        return cls(
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(UTC),
            model=data.get("model"),
            tokens_used=data.get("tokens_used"),
        )


@dataclass
class Conversation:
    """A collection of chat messages."""
    
    id: str = ""
    title: str = "New Conversation"
    messages: list[LLMMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    model: str = ""
    system_prompt: str | None = None
    total_tokens: int = 0
    
    def add_message(self, message: LLMMessage) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.updated_at = datetime.now(UTC)
        if message.tokens_used:
            self.total_tokens += message.tokens_used
    
    def get_messages_for_api(self) -> list[dict[str, str]]:
        """Get messages formatted for API request."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend([m.to_api_format() for m in self.messages])
        return messages
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "model": self.model,
            "system_prompt": self.system_prompt,
            "total_tokens": self.total_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Conversation":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", "New Conversation"),
            messages=[LLMMessage.from_dict(m) for m in data.get("messages", [])],
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(UTC),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.now(UTC),
            model=data.get("model", ""),
            system_prompt=data.get("system_prompt"),
            total_tokens=data.get("total_tokens", 0),
        )


# ============================================================================
# Model Information
# ============================================================================


@dataclass
class ModelPricing:
    """Model pricing information (per 1M tokens)."""
    
    prompt: float = 0.0
    completion: float = 0.0
    
    def to_dict(self) -> dict[str, float]:
        return {"prompt": self.prompt, "completion": self.completion}
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelPricing":
        return cls(
            prompt=float(data.get("prompt", 0)),
            completion=float(data.get("completion", 0)),
        )


@dataclass
class ModelInfo:
    """LLM model information."""
    
    id: str = ""
    name: str = ""
    description: str = ""
    context_length: int = 0
    pricing: ModelPricing = field(default_factory=ModelPricing)
    top_provider: str | None = None
    created: int | None = None
    
    @property
    def is_free(self) -> bool:
        """Check if model is free to use."""
        return self.pricing.prompt == 0 and self.pricing.completion == 0
    
    @property
    def provider(self) -> str:
        """Extract provider from model ID."""
        if "/" in self.id:
            return self.id.split("/")[0]
        return ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "context_length": self.context_length,
            "pricing": self.pricing.to_dict(),
            "top_provider": self.top_provider,
            "created": self.created,
        }
    
    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ModelInfo":
        """Create from OpenRouter API response.
        
        OpenRouter API returns pricing values already in USD per 1M tokens.
        For example, 0.50 means $0.50 per million tokens.
        """
        pricing_data = data.get("pricing", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", data.get("id", "")),
            description=data.get("description", ""),
            context_length=data.get("context_length", 0),
            pricing=ModelPricing(
                prompt=float(pricing_data.get("prompt", 0)),
                completion=float(pricing_data.get("completion", 0)),
            ),
            top_provider=data.get("top_provider", {}).get("name")
            if isinstance(data.get("top_provider"), dict)
            else None,
            created=data.get("created"),
        )
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelInfo":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            context_length=data.get("context_length", 0),
            pricing=ModelPricing.from_dict(data.get("pricing", {})),
            top_provider=data.get("top_provider"),
            created=data.get("created"),
        )


# ============================================================================
# Response Types
# ============================================================================


@dataclass
class LLMResponse:
    """Response from an LLM completion."""
    
    content: str = ""
    model: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    finish_reason: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_prompt + self.tokens_completion
    
    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "LLMResponse":
        """Create from OpenAI-compatible API response."""
        content = ""
        finish_reason = ""
        
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "")
        
        usage = data.get("usage", {})
        
        return cls(
            content=content,
            model=data.get("model", ""),
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            finish_reason=finish_reason,
            raw_response=data,
        )
