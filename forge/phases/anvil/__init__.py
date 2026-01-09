"""
Anvil Phase - Entity Management and Editing.

The Anvil phase provides:
- Entity viewing and editing
- Manual merge operations
- Relationship management
- Entity search and filtering
"""

from forge.phases.anvil.manager import EntityManager
from forge.phases.anvil.merger import EntityMerger
from forge.phases.anvil.orchestrator import AnvilOrchestrator

__all__ = [
    "EntityManager",
    "EntityMerger",
    "AnvilOrchestrator",
]
