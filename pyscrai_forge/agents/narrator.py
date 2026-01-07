"""The Narrator Agent: Responsible for weaving data into stories with fact-checking."""

import json
import logging
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from pyscrai_core import Entity, Relationship
from pyscrai_forge.prompts.narrative import (
    build_narrative_prompt,
    build_verification_prompt,
    NarrativeMode
)

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider

logger = logging.getLogger(__name__)

class NarratorAgent:
    """Weaves entities and relationships into cohesive narratives with fact-checking loops.
    
    Capabilities:
    - Multi-mode generation (SitRep, Story, Dossier)
    - Self-correction (verifies output against source data)
    - Entity possession (roleplay)
    """

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model

    async def generate_narrative(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        mode: NarrativeMode = NarrativeMode.SITREP,
        focus: str = "General Overview",
        context: str = ""
    ) -> str:
        """Generate a narrative based on the provided data, with self-correction.
        
        Args:
            entities: List of entities to include
            relationships: List of relationships connecting them
            mode: The style of narrative (SitRep, Story, etc.)
            focus: Specific angle or topic to focus on
            context: Additional background context
            
        Returns:
            Verified and refined narrative text
        """
        # 1. Prepare Data
        # Convert to lightweight dicts for the prompt to save tokens
        entity_data = [
            {
                "name": e.descriptor.name,
                "type": e.descriptor.entity_type.value,
                "resources": json.loads(e.state.resources_json or "{}")
            }
            for e in entities
        ]
        
        rel_data = [
            {
                "source": r.source_id, # In a real app, resolve names here for better prompting
                "target": r.target_id,
                "type": r.relationship_type.value,
                "desc": r.description
            }
            for r in relationships
        ]

        # 2. Draft Phase
        system_prompt, user_prompt = build_narrative_prompt(
            entity_data, rel_data, mode, focus, context
        )
        
        logger.info(f"Narrator: Generating draft in mode '{mode.value}'...")
        draft = await self.provider.complete_simple(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.model or self.provider.default_model,
            temperature=0.7 # Higher temp for creativity
        )

        # 3. Verification Phase (The "Editor" Loop)
        # We verify if the draft contradicts the hard data (e.g. wrong numbers/ranks)
        logger.info("Narrator: Verifying draft against source data...")
        
        verify_sys, verify_user = build_verification_prompt(draft, entity_data)
        critique = await self.provider.complete_simple(
            prompt=verify_user,
            system_prompt=verify_sys,
            model=self.model or self.provider.default_model,
            temperature=0.1 # Low temp for strict logic
        )

        # 4. Refinement Phase (if needed)
        if "PASS" in critique:
            logger.info("Narrator: Draft passed verification.")
            return draft
        else:
            logger.warning(f"Narrator: Draft failed verification. Critique: {critique}")
            logger.info("Narrator: Refining draft...")
            
            refine_prompt = (
                f"Original Request: {user_prompt}\n\n"
                f"Draft Generated:\n{draft}\n\n"
                f"Critique (Fact-Check Errors):\n{critique}\n\n"
                f"Task: Rewrite the narrative to fix the errors pointed out in the critique. "
                f"Maintain the style of a {mode.value}."
            )
            
            final_version = await self.provider.complete_simple(
                prompt=refine_prompt,
                system_prompt=system_prompt,
                model=self.model or self.provider.default_model,
                temperature=0.5
            )
            return final_version

    async def possess_entity(self, entity: Entity, user_input: str) -> str:
        """Roleplay as a specific entity (existing functionality)."""
        # (Keep your existing possession logic here or import it)
        # For this refactor, I am focusing on the generation loop.
        # Minimal implementation for compatibility:
        from pyscrai_forge.prompts.narrative import build_possession_system_prompt
        
        entity_data = json.loads(entity.model_dump_json())
        sys_prompt = build_possession_system_prompt(entity_data)
        
        response = await self.provider.complete_simple(
            prompt=user_input,
            system_prompt=sys_prompt,
            model=self.model or self.provider.default_model
        )
        return response