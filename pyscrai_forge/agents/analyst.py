"""The Analyst Agent: Responsible for data mining and schema population."""

import json
import re
from typing import TYPE_CHECKING
from pyscrai_core import (
    Entity, Actor, Polity, Location, 
    StateComponent, DescriptorComponent, SpatialComponent, 
    LocationLayer, EntityType
)
from pyscrai_forge.src.prompts import get_analyst_prompt
from .models import EntityStub

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider

class AnalystAgent:
    """Populates entity stats based on Project Schema."""

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model

    async def analyze_entity(
        self, 
        stub: EntityStub, 
        text: str, 
        schema: dict[str, str]
    ) -> Entity:
        """Deep dive analysis to fill StateComponent resources."""
        
        # If schema is empty, we don't need to ask LLM, just build basic entity
        if not schema:
            return self._build_entity(stub, {})

        system_prompt, user_prompt = get_analyst_prompt(
            text, 
            stub.name, 
            stub.entity_type.value, 
            schema, 
            stub.description
        )

        try:
            response = await self.provider.complete_simple(
                prompt=user_prompt,
                model=self.model,
                system_prompt=system_prompt,
                temperature=0.1
            )
            resources = self._parse_response(response)
            return self._build_entity(stub, resources)
        except Exception as e:
            print(f"Analyst failed for {stub.name}: {e}")
            return self._build_entity(stub, {})

    def _parse_response(self, response: str) -> dict:
        """Parse JSON response."""
        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match: cleaned = match.group(1)
            elif "```" in cleaned:
                match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match: cleaned = match.group(1)
                
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
        
        # Helper logic for Location Layers (could be extracted by Analyst too if added to schema)
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
