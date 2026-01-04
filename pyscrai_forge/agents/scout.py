"""The Scout Agent: Responsible for entity discovery."""

import json
import re
from typing import TYPE_CHECKING
from pyscrai_core import EntityType
from pyscrai_forge.prompts.core import Genre
from pyscrai_forge.prompts.narrative import get_scout_prompt
from pyscrai_forge.agents.models import EntityStub

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider

class ScoutAgent:
    """Discovers entities in text without deep analysis."""

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model

    async def discover_entities(self, text: str, genre: Genre = Genre.GENERIC) -> list[EntityStub]:
        """Scan text for potential entities."""
        system_prompt, user_prompt = get_scout_prompt(text, genre)
        
        try:
            # Use model if provided, otherwise use provider's default (same pattern as Analyst/Narrator)
            response = await self.provider.complete_simple(
                prompt=user_prompt,
                model=self.model or self.provider.default_model,
                system_prompt=system_prompt,
                temperature=0.1
            )
            return self._parse_response(response)
        except Exception as e:
            # Re-raise with more context instead of silently returning empty list
            raise RuntimeError(f"Scout phase failed: {e}") from e

    def _parse_response(self, response: str) -> list[EntityStub]:
        """Parse JSON response into EntityStubs."""
        try:
            # Clean markdown
            cleaned = response.strip()
            if "```json" in cleaned:
                match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match: cleaned = match.group(1)
            elif "```" in cleaned:
                match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match: cleaned = match.group(1)
            
            data = json.loads(cleaned)
            stubs = []
            
            for item in data.get("entities", []):
                try:
                    # Robust type parsing
                    t_str = item.get("entity_type", "abstract").lower()
                    try:
                        e_type = EntityType(t_str)
                    except ValueError:
                        e_type = EntityType.ABSTRACT
                        
                    stubs.append(EntityStub(
                        id=item.get("id"),
                        name=item.get("name", "Unknown"),
                        entity_type=e_type,
                        description=item.get("description", ""),
                        aliases=item.get("aliases", []),
                        tags=set(item.get("tags", []))
                    ))
                except Exception:
                    continue
                    
            return stubs
            
        except json.JSONDecodeError:
            return []
