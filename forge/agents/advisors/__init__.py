"""
Advisors - Phase-specific AI assistants.

Each advisor is tied to a specific phase and loaded with
personality/prompts from agents/prompts/advisors/.

UI Label Mapping:
- OSINT  → Phase 0: Extraction
- HUMINT → Phase 1: Entities
- SIGINT → Phase 2: Relationships
- SYNTH  → Phase 3: Narrative
- GEOINT → Phase 4: Map
- ANVIL  → Phase 5: Finalize
"""

from forge.agents.advisors.osint_advisor import OSINTAdvisor
from forge.agents.advisors.humint_advisor import HUMINTAdvisor
from forge.agents.advisors.sigint_advisor import SIGINTAdvisor
from forge.agents.advisors.synth_advisor import SYNTHAdvisor
from forge.agents.advisors.geoint_advisor import GEOINTAdvisor
from forge.agents.advisors.anvil_advisor import ANVILAdvisor

__all__ = [
    "OSINTAdvisor",
    "HUMINTAdvisor",
    "SIGINTAdvisor",
    "SYNTHAdvisor",
    "GEOINTAdvisor",
    "ANVILAdvisor",
]
