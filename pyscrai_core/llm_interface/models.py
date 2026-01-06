"""Data models for LLM interactions in PyScrAI."""

from pyscrai_core.models import generate_intuitive_id
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatMessage:
    """A single chat message."""

    id: str = field(default_factory=lambda: generate_intuitive_id("CHAT"))
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    model: str | None = None  # Model used for assistant messages
    tokens_used: int | None = None

    def to_api_format(self) -> dict:
        """Convert to OpenRouter/OpenAI API message format."""
        return {
            "role": self.role.value,
            "content": self.content,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "tokens_used": self.tokens_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        """Create from dictionary."""
        return cls(
            id=data.get("id", generate_intuitive_id("CHAT")),
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

    id: str = field(default_factory=lambda: generate_intuitive_id("CONV"))
    title: str = "New Conversation"
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    model: str = ""  # Default model for this conversation
    system_prompt: str | None = None
    total_tokens: int = 0

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.updated_at = datetime.now(UTC)
        if message.tokens_used:
            self.total_tokens += message.tokens_used

    def get_messages_for_api(self) -> list[dict]:
        """Get messages formatted for API request."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend([m.to_api_format() for m in self.messages])
        return messages

    def generate_title(self) -> str:
        """Generate a title from the first user message."""
        for msg in self.messages:
            if msg.role == MessageRole.USER:
                # Take first 50 chars of first user message
                title = msg.content[:50]
                if len(msg.content) > 50:
                    title += "..."
                return title
        return "New Conversation"

    def to_dict(self) -> dict:
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
    def from_dict(cls, data: dict) -> "Conversation":
        """Create from dictionary."""
        return cls(
            id=data.get("id", generate_intuitive_id("CONV")),
            title=data.get("title", "New Conversation"),
            messages=[ChatMessage.from_dict(m) for m in data.get("messages", [])],
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


@dataclass
class ModelPricing:
    """Model pricing information."""

    prompt: float = 0.0  # Price per 1M tokens
    completion: float = 0.0  # Price per 1M tokens

    def to_dict(self) -> dict:
        return {"prompt": self.prompt, "completion": self.completion}

    @classmethod
    def from_dict(cls, data: dict) -> "ModelPricing":
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

    def to_dict(self) -> dict:
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
    def from_api_response(cls, data: dict) -> "ModelInfo":
        """Create from OpenRouter API response."""
        pricing_data = data.get("pricing", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", data.get("id", "")),
            description=data.get("description", ""),
            context_length=data.get("context_length", 0),
            pricing=ModelPricing(
                prompt=float(pricing_data.get("prompt", 0)) * 1_000_000,
                completion=float(pricing_data.get("completion", 0)) * 1_000_000,
            ),
            top_provider=data.get("top_provider", {}).get("name")
            if isinstance(data.get("top_provider"), dict)
            else None,
            created=data.get("created"),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ModelInfo":
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


@dataclass
class Generation:
    """A generation history entry from LLM provider."""

    id: str = ""
    model: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_cost: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
            "total_cost": self.total_cost,
        }

    @classmethod
    def from_api_response(cls, data: dict) -> "Generation":
        """Create from OpenRouter API response."""
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            if "created_at" in data
            else datetime.now(UTC),
            tokens_prompt=data.get("tokens_prompt", 0),
            tokens_completion=data.get("tokens_completion", 0),
            total_cost=data.get("total_cost", 0.0),
        )
