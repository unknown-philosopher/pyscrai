from dataclasses import dataclass
from enum import Enum

class Genre(str, Enum):
    """Document genre for context-appropriate extraction."""
    HISTORICAL = "historical"
    FANTASY = "fantasy"
    SCIFI = "scifi"
    MODERN = "modern"
    GENERIC = "generic"

@dataclass
class PromptTemplate:
    """Container for extraction prompt configuration."""
    system_prompt: str
    user_prompt_template: str
    genre: Genre
    target_entities: list[str]