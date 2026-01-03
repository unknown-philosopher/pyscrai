"""The Narrator Agent: Scenario generation and entity possession.

This agent handles creative writing tasks: generating scenarios from entity data
and roleplaying as entities for interactive simulation.
"""

import json
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from pyscrai_forge.prompts.narrative import (
    build_scenario_prompt,
    build_possession_system_prompt,
)

if TYPE_CHECKING:
    from pyscrai_core import Entity
    from pyscrai_core.llm_interface import LLMProvider


class NarratorAgent:
    """Narrator agent for scenario generation and entity possession.
    
    Responsibilities:
    - Scenario generation: Create narratives from entity/relationship data
    - Entity possession: Roleplay as entities for interactive simulation
    """

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model

    async def generate_scenario(
        self,
        corpus_data: List[Dict[str, Any]],
        project_config: Dict[str, Any],
        focus: Optional[str] = None
    ) -> str:
        """Generate a data-driven narrative scenario.
        
        Args:
            corpus_data: List of entity/relationship data dictionaries
            project_config: Project manifest and configuration
            focus: Optional focus area or scope for the scenario
            
        Returns:
            Generated scenario text
        """
        system_prompt, user_prompt = build_scenario_prompt(
            corpus_data,
            project_config,
            focus
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # In the future, we would add tools: [{ "google_search": {} }] here for verification
        try:
            response = await self.provider.complete(
                messages=messages,
                model=self.model or self.provider.default_model
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error generating scenario: {e}"

    async def possess_entity(
        self,
        entity: "Entity",
        user_input: str,
        context_summary: str = ""
    ) -> str:
        """Handle entity possession/roleplay interaction.
        
        Args:
            entity: The entity to roleplay as
            user_input: User's input/query
            context_summary: Current world state context
            
        Returns:
            Response from the entity's perspective
        """
        entity_data = json.loads(entity.model_dump_json())
        system_prompt = build_possession_system_prompt(entity_data, context_summary)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response = await self.provider.complete(
                messages=messages,
                model=self.model or self.provider.default_model,
                temperature=0.8
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error in possession: {e}"
