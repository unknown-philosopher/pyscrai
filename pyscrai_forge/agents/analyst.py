"""The Analyst Agent: Unified data extraction and refinement.

This agent combines entity extraction (from harvester/analyst.py) and
JSON refinement (from architect/sub_agents.py JSONRefiner) into a single
unified agent responsible for data processing.
"""

import json
import re
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

        try:
            response = await self.provider.complete_simple(
                prompt=user_prompt,
                model=self.model or self.provider.default_model,
                system_prompt=system_prompt,
                temperature=0.1
            )
            resources = self._parse_response(response)
            return self._build_entity(stub, resources)
        except Exception as e:
            print(f"Analyst extraction failed for {stub.name}: {e}")
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
        
        state = StateComponent(resources_json=json.dumps(resources))
        
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
