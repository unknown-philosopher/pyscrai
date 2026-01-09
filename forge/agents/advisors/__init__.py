"""
Advisors - Module-specific AI assistants.

Each advisor is tied to a specific phase and loaded with
personality/prompts from prefabs/advisors/.
"""

from forge.agents.advisors.entity_advisor import EntityAdvisor
from forge.agents.advisors.relationship_advisor import RelationshipAdvisor

__all__ = [
    "EntityAdvisor",
    "RelationshipAdvisor",
]
