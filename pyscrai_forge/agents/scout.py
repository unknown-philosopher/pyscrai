"""The Scout Agent: Responsible for entity discovery."""

import json
import re
import logging
from typing import TYPE_CHECKING, Optional
from pyscrai_core import EntityType
from pyscrai_forge.prompts.core import Genre
from pyscrai_forge.prompts.template_manager import TemplateManager
from pyscrai_forge.agents.models import EntityStub

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider

logger = logging.getLogger(__name__)

class ScoutAgent:
    """Discovers entities in text without deep analysis."""

    def __init__(self, provider: "LLMProvider", model: str | None = None, template_manager: Optional[TemplateManager] = None):
        self.provider = provider
        self.model = model
        self.template_manager = template_manager or TemplateManager()

    async def discover_entities(self, text: str, genre: Genre = Genre.GENERIC, template_name: Optional[str] = None) -> list[EntityStub]:
        """Scan text for potential entities using template system.
        
        Args:
            text: Text to scan for entities
            genre: Document genre for template selection
            template_name: Optional custom template directory name to use (overrides genre mapping)
            
        Returns:
            List of EntityStub objects
        """
        # If template_name is explicitly provided, use it as the template directory
        if template_name:
            template_genre = template_name
            logger.info(f"Scout: Using explicit template_name='{template_name}' as template_genre")
            allow_fallback = False  # Don't fallback when template_name is explicitly provided
        else:
            # Load template (uses genre mapping: "generic" -> "default", etc)
            genre_map = {
                Genre.GENERIC.value: "default",
                Genre.HISTORICAL.value: "historical",
                "historical": "historical",
                "espionage": "espionage",
                "fictional": "fictional",
            }
            template_genre = genre_map.get(genre.value if hasattr(genre, 'value') else genre, "default")
            logger.info(f"Scout: Using genre-based template selection: genre={genre} -> template_genre='{template_genre}'")
            allow_fallback = True  # Allow fallback for genre-based selection
        
        try:
            template = self.template_manager.get_template(
                "scout",
                genre=template_genre,
                allow_fallback=allow_fallback
            )
            logger.info(f"Scout: Successfully loaded template from genre='{template_genre}'")
        except (FileNotFoundError, ValueError) as e:
            if not allow_fallback:
                # If template_name was explicitly provided, fail instead of falling back
                error_type = "not found" if isinstance(e, FileNotFoundError) else "empty or malformed"
                logger.error(f"Scout: Template '{template_genre}' {error_type}, but template_name was explicitly provided. Failing.")
                raise RuntimeError(
                    f"Template '{template_genre}' {error_type}. "
                    f"Since template_name='{template_name}' was explicitly provided, falling back to default is not allowed. "
                    f"Please ensure the template directory exists and contains a valid scout.yaml file."
                ) from e
            # Fallback to default only for genre-based selection
            logger.warning(f"Scout: Template '{template_genre}' not found or invalid, falling back to 'default'")
            template = self.template_manager.get_template("scout", genre="default", allow_fallback=True)
        
        # Render template with text
        system_prompt, user_prompt = template.render(text=text, genre=genre.value if hasattr(genre, 'value') else genre)
        
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
                    
                    # Generate ID if not provided
                    entity_id = item.get("id")
                    if not entity_id:
                        from pyscrai_core.models import generate_intuitive_id
                        entity_id = generate_intuitive_id("ENTITY")
                        
                    stubs.append(EntityStub(
                        id=entity_id,
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
