"""The Analyst Agent: Unified data extraction and refinement.

This agent combines entity extraction (from harvester/analyst.py) and
JSON refinement (from architect/sub_agents.py JSONRefiner) into a single
unified agent responsible for data processing.
"""

import json
import re
import logging
from typing import TYPE_CHECKING, Dict, Any

from pyscrai_core import (
    Entity, Actor, Polity, Location,
    StateComponent, DescriptorComponent, SpatialComponent,
    LocationLayer, EntityType
)

from pyscrai_forge.prompts.analysis import (
    build_extraction_prompt,
    build_refinement_prompt,
)
from pyscrai_forge.agents.models import EntityStub

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider

logger = logging.getLogger(__name__)


class AnalystAgent:
    """Unified Analyst agent for extraction and refinement.
    
    Responsibilities:
    - Entity extraction: Extract entities and stats from raw text
    - Data refinement: Clean, structure, and validate JSON data
    """

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model

    async def extract_from_text(
        self,
        stub: EntityStub,
        text: str,
        schema: dict[str, str]
    ) -> Entity:
        """Extract entity data from text (from harvester/analyst.py analyze_entity).
        
        Args:
            stub: Entity stub with basic information
            text: Source text to analyze
            schema: Project schema defining fields to extract
            
        Returns:
            Full Entity with extracted resources
        """
        # If schema is empty, we don't need to ask LLM, just build basic entity
        if not schema:
            return self._build_entity(stub, {})

        system_prompt, user_prompt = build_extraction_prompt(
            text,
            stub.name,
            stub.entity_type.value,
            schema,
            stub.description
        )

        # Verbose logging: Show prompts
        logger.debug("=" * 80)
        logger.debug(f"ANALYST AGENT - Extracting data for: {stub.name} ({stub.entity_type.value})")
        logger.debug("=" * 80)
        logger.debug(f"Model: {self.model or self.provider.default_model}")
        logger.debug(f"Temperature: 0.1")
        logger.debug(f"Schema fields: {list(schema.keys()) if schema else 'None'}")
        logger.debug("\n--- SYSTEM PROMPT ---")
        logger.debug(system_prompt)
        logger.debug("\n--- USER PROMPT ---")
        logger.debug(user_prompt)
        logger.debug("\n--- Sending request to LLM ---")

        attempts = 0
        max_attempts = 2
        
        while attempts < max_attempts:
            try:
                response = await self.provider.complete_simple(
                    prompt=user_prompt,
                    model=self.model or self.provider.default_model,
                    system_prompt=system_prompt,
                    temperature=0.1
                )
                
                # Verbose logging: Show response
                logger.debug(f"\n--- LLM RESPONSE (Attempt {attempts + 1}) ---")
                logger.debug(response)
                
                resources = self._parse_response(response)
                
                logger.debug(f"--- Parsed Resources ---")
                logger.debug(json.dumps(resources, indent=2))
                
                # --- LAZINESS CHECK ---
                # If schema has keys but resources is empty, and text is long enough, likely failure.
                if schema and not resources and len(text) > 20:
                    attempts += 1
                    if attempts < max_attempts:
                        logger.warning(
                            f"Analyst returned empty resources for {stub.name}. "
                            f"Retrying with strict instruction (attempt {attempts + 1}/{max_attempts})."
                        )
                        logger.debug("--- Adding retry instruction to prompt ---")
                        user_prompt += (
                            "\n\nCRITICAL: You returned empty JSON. "
                            "You MUST extract attributes like Rank, Unit, Status, Wealth, or other schema fields "
                            "if they are present in the text. Do not leave the resources object empty if the text "
                            "contains relevant information."
                        )
                        continue
                
                logger.debug("=" * 80)
                return self._build_entity(stub, resources)
            except Exception as e:
                attempts += 1
                logger.debug(f"--- Exception occurred (Attempt {attempts}) ---")
                logger.debug(f"Error: {e}")
                if attempts >= max_attempts:
                    logger.error(f"Analyst extraction failed for {stub.name} after {max_attempts} attempts: {e}")
                    logger.debug("=" * 80)
                    return self._build_entity(stub, {})
                # Retry on exception
                continue
        
        # Fallback if loop exits without return
        return self._build_entity(stub, {})

    async def refine_data(
        self,
        raw_data: Dict[str, Any],
        schema_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refine and structure raw JSON data (from JSONRefiner.refine).
        
        Args:
            raw_data: Raw JSON data to refine
            schema_context: Project schema and context for validation
            
        Returns:
            Refined and structured JSON data
        """
        system_prompt, user_prompt = build_refinement_prompt(
            raw_data,
            schema_context
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.provider.complete(
                messages=messages,
                model=self.model or self.provider.default_model
            )
            content = response["choices"][0]["message"]["content"]
            
            # Extract JSON block
            try:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    return json.loads(content[start:end+1])
                else:
                    return {"error": "No JSON found in response", "raw": content}
            except json.JSONDecodeError as e:
                return {"error": f"Failed to parse refined JSON: {e}", "raw": content}
        except Exception as e:
            return {"error": f"Refinement failed: {e}", "raw": raw_data}

    def _parse_response(self, response: str) -> dict:
        """Parse JSON response from LLM."""
        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
            elif "```" in cleaned:
                match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
                
            data = json.loads(cleaned)
            return data.get("resources", {})
        except (json.JSONDecodeError, AttributeError):
            return {}

    def _build_entity(self, stub: EntityStub, resources: dict) -> Entity:
        """Convert Stub + Resources -> Full Entity."""
        
        descriptor = DescriptorComponent(
            name=stub.name,
            entity_type=stub.entity_type,
            bio=stub.description,
            aliases=stub.aliases,
            tags=stub.tags
        )
        
        # Filter out fields that duplicate DescriptorComponent data
        # These fields are already stored in descriptor, so we don't need them in resources_json
        filtered_resources = {
            k: v for k, v in resources.items()
            if k not in ["name", "description", "tags"]
        }
        
        state = StateComponent(resources_json=json.dumps(filtered_resources))
        
        # Helper logic for Location Layers
        spatial = None
        if stub.entity_type == EntityType.LOCATION:
            spatial = SpatialComponent(layer=LocationLayer.TERRESTRIAL)

        # Factory
        if stub.entity_type == EntityType.ACTOR:
            return Actor(id=stub.id, descriptor=descriptor, state=state, spatial=spatial)
        elif stub.entity_type == EntityType.POLITY:
            return Polity(id=stub.id, descriptor=descriptor, state=state, spatial=spatial)
        elif stub.entity_type == EntityType.LOCATION:
            return Location(id=stub.id, descriptor=descriptor, state=state, spatial=spatial)
        else:
            return Entity(id=stub.id, descriptor=descriptor, state=state, spatial=spatial)
