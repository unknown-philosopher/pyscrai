"""Phase 1: FOUNDRY - Entity Extraction and Staging.

The Foundry phase handles:
- Document import and text extraction
- Entity extraction via Scout/Analyst agents
- Entity editing and validation
- Staging output to entities_staging.json

Output artifact: staging/entities_staging.json
"""

from pyscrai_forge.phases.foundry.ui import FoundryPanel
from pyscrai_forge.phases.foundry.assistant import FoundryAssistant, AliasSuggestion

__all__ = ["FoundryPanel", "FoundryAssistant", "AliasSuggestion"]

