"""
Phase 5 Finalize (UI: ANVIL) - Entity Management and Editing.

The Finalize phase provides:
- Entity viewing and editing
- Manual merge operations
- Relationship management
- Entity search and filtering
"""

from forge.phases.p5_finalize.manager import EntityManager
from forge.phases.p5_finalize.merger import EntityMerger
from forge.phases.p5_finalize.orchestrator import FinalizeOrchestrator

__all__ = [
    "EntityManager",
    "EntityMerger",
    "FinalizeOrchestrator",
]
