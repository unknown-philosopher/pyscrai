"""The Narrator Agent: Scenario generation and entity possession.

This agent handles creative writing tasks: generating scenarios from entity data
and roleplaying as entities for interactive simulation.
"""

import json
import logging
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from pyscrai_forge.prompts.narrative import (
    build_scenario_prompt,
    build_possession_system_prompt,
    build_narrative_prompt,
    build_verification_prompt,
    NarrativeMode,
)

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship
    from pyscrai_core.llm_interface import LLMProvider

logger = logging.getLogger(__name__)


class NarratorAgent:
    """Narrator agent for scenario generation and entity possession.

    Enhancements:
    - generate_narrative: multi-mode generation with a self-check loop
    - generate_scenario: compatibility wrapper that uses generate_narrative
    - possess_entity: roleplay using `complete_simple` for consistency
    """

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model

    async def generate_narrative(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        mode: NarrativeMode = NarrativeMode.SUMMARY,
        focus: str = "General Overview",
        context: str = ""
    ) -> str:
        """Generate a narrative with a verify-and-refine loop.

        Args:
            entities: List of entity dictionaries (lightweight)
            relationships: List of relationship dictionaries
            mode: NarrativeMode to control tone/format
            focus: Focus area for the narrative
            context: Optional background context

        Returns:
            Verified narrative text
        """
        # Build prompts
        system_prompt, user_prompt = build_narrative_prompt(
            entities, relationships, mode, focus, context
        )

        model = self.model or self.provider.default_model

        try:
            logger.info("Narrator: Generating draft...")
            draft = await self.provider.complete_simple(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=0.7,
            )

            logger.info("Narrator: Verifying draft against source data...")
            verify_sys, verify_user = build_verification_prompt(draft, entities)
            critique = await self.provider.complete_simple(
                prompt=verify_user,
                system_prompt=verify_sys,
                model=model,
                temperature=0.1,
            )

            if critique and "PASS" in critique.upper():
                logger.info("Narrator: Draft passed verification.")
                return draft

            # If verification failed, ask for a refined version
            logger.warning("Narrator: Draft failed verification. Critique found. Refining...")
            refine_prompt = (
                f"Original Request:\n{user_prompt}\n\n"
                f"Draft Generated:\n{draft}\n\n"
                f"Critique (Fact-Check Errors):\n{critique}\n\n"
                f"Task: Rewrite the narrative to fix the errors pointed out in the critique. "
                f"Maintain the style of a {mode.value}."
            )

            final_version = await self.provider.complete_simple(
                prompt=refine_prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=0.5,
            )
            return final_version

        except Exception as e:
            logger.exception("Narrator: Error during narrative generation")
            return f"Error generating narrative: {e}"

    async def generate_scenario(
        self,
        corpus_data: List[Dict[str, Any]],
        project_config: Dict[str, Any],
        focus: Optional[str] = None
    ) -> str:
        """Backward-compatible wrapper used by ForgeManager.

        Converts corpus_data (list of entity dicts) into the lightweight format
        expected by `generate_narrative` and runs the verified generation loop.
        """
        # Convert corpus_data to lightweight entity dicts for prompting
        entities = []
        relationships = []
        for item in corpus_data:
            ent = {
                "id": item.get("id"),
                "name": item.get("descriptor", {}).get("name") if isinstance(item.get("descriptor"), dict) else item.get("name"),
                "type": item.get("descriptor", {}).get("entity_type") if isinstance(item.get("descriptor"), dict) else item.get("entity_type"),
                "resources": json.loads(item.get("state", {}).get("resources_json", "{}")) if isinstance(item.get("state"), dict) else item.get("resources", {})
            }
            entities.append(ent)

        mode = NarrativeMode.SUMMARY
        focus_text = focus or "General Overview"
        context = f"Project Config:\n{json.dumps(project_config, indent=2)}"

        return await self.generate_narrative(entities, relationships, mode=mode, focus=focus_text, context=context)

    async def possess_entity(
        self,
        entity: "Entity",
        user_input: str,
        context_summary: str = ""
    ) -> str:
        """Roleplay as a specific entity (keeps previous behavior)."""
        entity_data = json.loads(entity.model_dump_json())
        sys_prompt = build_possession_system_prompt(entity_data, context_summary)

        try:
            response = await self.provider.complete_simple(
                prompt=user_input,
                system_prompt=sys_prompt,
                model=self.model or self.provider.default_model,
                temperature=0.8,
            )
            return response
        except Exception as e:
            logger.exception("Narrator: Error in possession")
            return f"Error in possession: {e}"
