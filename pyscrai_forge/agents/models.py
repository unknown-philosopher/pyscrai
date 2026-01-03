"""Shared data models for the Agentic Architecture."""

from dataclasses import dataclass, field
from typing import Any, Optional
from pyscrai_core import EntityType

@dataclass
class EntityStub:
    """Lightweight entity representation for the Scout phase."""
    id: str
    name: str
    entity_type: EntityType
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)
    # Source text context for the Analyst
    source_chunk_id: Optional[int] = None 
