"""Shared data models for PyScrAI|Forge agents.

This module defines Pydantic models and data classes used for agent communication
and data structures shared across the unified Forge architecture.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from pyscrai_core import EntityType

# =============================================================================
# ENTITY STUB (moved from harvester/models.py)
# =============================================================================

@dataclass
class EntityStub:
    """Lightweight entity representation for discovery/extraction phases."""
    id: str
    name: str
    entity_type: EntityType
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)
    # Source text context for the Analyst
    source_chunk_id: Optional[int] = None

__all__ = ["EntityStub"]
