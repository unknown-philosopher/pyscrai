"""The Analyst Agent: Unified data extraction and refinement.

This agent combines entity extraction (from harvester/analyst.py) and
JSON refinement (from architect/sub_agents.py JSONRefiner) into a single
unified agent responsible for data processing.
"""

import json
import re
import logging
from typing import TYPE_CHECKING, Dict, Any, Optional

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
from pyscrai_forge.prompts.template_manager import TemplateManager
from pyscrai_forge.prompts.core import Genre

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider

logger = logging.getLogger(__name__)


class AnalystAgent:
    """Unified Analyst agent for extraction and refinement.
    
    Responsibilities:
    - Entity extraction: Extract entities and stats from raw text
    - Data refinement: Clean, structure, and validate JSON data
    """

    def __init__(self, provider: "LLMProvider", model: str | None = None, template_manager: Optional[TemplateManager] = None, memory_service=None, project_path=None):
        self.provider = provider
        self.model = model
        self.template_manager = template_manager or TemplateManager()
        self.memory_service = memory_service
        self.project_path = project_path

    async def extract_from_text(
        self,
        stub: EntityStub,
        text: str,
        schema: dict[str, str],
        genre: Genre = Genre.GENERIC,
        template_name: Optional[str] = None
    ) -> Entity:
        """Extract entity data from text (from harvester/analyst.py analyze_entity).
        
        Args:
            stub: Entity stub with basic information
            text: Source text to analyze
            schema: Project schema defining fields to extract
            genre: Document genre for template selection
            template_name: Optional custom template directory name to use (overrides genre mapping)
            
        Returns:
            Full Entity with extracted resources
        """
        # If schema is empty, we don't need to ask LLM, just build basic entity
        if not schema:
            return self._build_entity(stub, {})

        # Use TemplateManager to load analyst.yaml template instead of hardcoded prompt
        template = None
        try:
            # Determine template genre (same logic as Scout)
            if template_name:
                template_genre = template_name
                logger.info(f"Analyst: Using explicit template_name='{template_name}' as template_genre")
                allow_fallback = False
            else:
                genre_map = {
                    Genre.GENERIC.value: "default",
                    Genre.HISTORICAL.value: "historical",
                    "historical": "historical",
                    "espionage": "espionage",
                    "fictional": "fictional",
                }
                template_genre = genre_map.get(genre.value if hasattr(genre, 'value') else genre, "default")
                logger.info(f"Analyst: Using genre-based template selection: genre={genre} -> template_genre='{template_genre}'")
                allow_fallback = True
            
            try:
                template = self.template_manager.get_template(
                    "analyst",
                    genre=template_genre,
                    allow_fallback=allow_fallback
                )
                logger.info(f"Analyst: Successfully loaded template from genre='{template_genre}'")
            except (FileNotFoundError, ValueError) as e:
                if not allow_fallback:
                    error_type = "not found" if isinstance(e, FileNotFoundError) else "empty or malformed"
                    logger.error(f"Analyst: Template '{template_genre}' {error_type}, but template_name was explicitly provided. Falling back to hardcoded prompt.")
                    template = None  # Will use fallback below
                else:
                    logger.warning(f"Analyst: Template '{template_genre}' not found or invalid, falling back to 'default'")
                    try:
                        template = self.template_manager.get_template("analyst", genre="default", allow_fallback=True)
                    except Exception:
                        template = None  # Will use fallback below
            
            # Render template with variables if successfully loaded (full description, no truncation)
            if template is not None:
                schema_fields = json.dumps(schema, indent=2) if schema else "{}"
                system_prompt, user_prompt = template.render(
                    text=text,
                    entity_name=stub.name,
                    entity_type=stub.entity_type.value,
                    description=stub.description or "",  # Full description, no truncation
                    schema_fields=schema_fields,
                    genre=genre.value if hasattr(genre, 'value') else str(genre)
                )
            else:
                # Fallback to hardcoded prompt if template loading failed
                logger.warning(f"Analyst: Using hardcoded prompt as fallback")
                system_prompt, user_prompt = build_extraction_prompt(
                    text,
                    stub.name,
                    stub.entity_type.value,
                    schema,
                    stub.description  # Full description, no truncation
                )
        except Exception as e:
            # Fallback to hardcoded prompt if template loading fails
            logger.warning(f"Analyst: Failed to load template, falling back to hardcoded prompt: {e}")
            system_prompt, user_prompt = build_extraction_prompt(
                text,
                stub.name,
                stub.entity_type.value,
                schema,
                stub.description  # Full description, no truncation
            )

        # RAG: Retrieve historical context before calling LLM
        context_sentence = self._extract_context_sentence(text, stub.name)
        historical_briefing = self._get_historical_briefing(stub, text)
        
        if historical_briefing:
            user_prompt = historical_briefing + "\n\n" + user_prompt
            logger.debug("\n--- HISTORICAL CONTEXT BRIEFING ---")
            logger.debug(historical_briefing)
        
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
                entity = self._build_entity(stub, resources)
                # Store context sentence for alias detection
                if context_sentence and hasattr(entity, 'descriptor') and entity.descriptor:
                    # Store in descriptor bio or as metadata
                    if not entity.descriptor.bio:
                        entity.descriptor.bio = context_sentence
                    elif context_sentence not in entity.descriptor.bio:
                        # Append if not already present
                        entity.descriptor.bio = entity.descriptor.bio + " " + context_sentence
                return entity
            except Exception as e:
                attempts += 1
                logger.debug(f"--- Exception occurred (Attempt {attempts}) ---")
                logger.debug(f"Error: {e}")
                if attempts >= max_attempts:
                    logger.error(f"Analyst extraction failed for {stub.name} after {max_attempts} attempts: {e}")
                    logger.debug("=" * 80)
                    entity = self._build_entity(stub, {})
                    # Store context sentence even on failure
                    context_sentence = self._extract_context_sentence(text, stub.name)
                    if context_sentence and hasattr(entity, 'descriptor') and entity.descriptor:
                        if not entity.descriptor.bio:
                            entity.descriptor.bio = context_sentence
                    return entity
                # Retry on exception
                continue
        
        # Fallback if loop exits without return
        entity = self._build_entity(stub, {})
        context_sentence = self._extract_context_sentence(text, stub.name)
        if context_sentence and hasattr(entity, 'descriptor') and entity.descriptor:
            if not entity.descriptor.bio:
                entity.descriptor.bio = context_sentence
        return entity

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
            
            # Handle case where data is a list instead of dict
            if isinstance(data, list):
                logger.warning(f"LLM returned a list instead of dict, converting to dict")
                # Try to convert list to dict if it's a list of key-value pairs
                if len(data) > 0 and isinstance(data[0], dict):
                    # Merge all dicts in the list
                    result = {}
                    for item in data:
                        if isinstance(item, dict):
                            result.update(item)
                    return result
                return {}
            
            # Handle case where data is a dict
            if isinstance(data, dict):
                resources = data.get("resources", {})
                # Ensure resources is a dict, not a list
                if isinstance(resources, list):
                    logger.warning(f"LLM returned resources as a list, converting to dict")
                    if len(resources) > 0 and isinstance(resources[0], dict):
                        # Merge all dicts in the list
                        result = {}
                        for item in resources:
                            if isinstance(item, dict):
                                result.update(item)
                        return result
                    return {}
                return resources if isinstance(resources, dict) else {}
            
            return {}
        except (json.JSONDecodeError, AttributeError) as e:
            logger.debug(f"Failed to parse response: {e}")
            return {}

    def _extract_context_sentence(self, text: str, entity_name: str) -> str:
        """Extract the sentence or paragraph where entity was mentioned.
        
        Args:
            text: Full source text
            entity_name: Name of the entity to find
            
        Returns:
            Context sentence/paragraph containing the entity mention
        """
        if not text or not entity_name:
            return ""
        
        # Find all occurrences of the entity name
        pattern = re.escape(entity_name)
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        
        if not matches:
            return ""
        
        # Get the first match and extract surrounding context
        first_match = matches[0]
        start = first_match.start()
        
        # Extract sentence: find previous period/exclamation/question mark, then next one
        sentence_start = max(0, text.rfind('.', 0, start))
        if sentence_start == -1:
            sentence_start = max(0, text.rfind('!', 0, start))
        if sentence_start == -1:
            sentence_start = max(0, text.rfind('?', 0, start))
        if sentence_start == -1:
            sentence_start = 0
        else:
            sentence_start += 1  # Skip the punctuation
        
        sentence_end = text.find('.', start)
        if sentence_end == -1:
            sentence_end = text.find('!', start)
        if sentence_end == -1:
            sentence_end = text.find('?', start)
        if sentence_end == -1:
            sentence_end = len(text)
        else:
            sentence_end += 1  # Include the punctuation
        
        context = text[sentence_start:sentence_end].strip()
        
        # If context is too short, try to get a larger window (paragraph)
        if len(context) < 50:
            # Get a larger window (up to 200 chars)
            window_start = max(0, start - 100)
            window_end = min(len(text), start + len(entity_name) + 100)
            context = text[window_start:window_end].strip()
        
        return context
    
    def _get_historical_briefing(self, stub: EntityStub, text: str) -> str:
        """Retrieve historical context from world.db using RAG.
        
        Args:
            stub: Entity stub being extracted
            text: Source text
            
        Returns:
            Historical briefing string (empty if no context found)
        """
        if not self.memory_service or not self.project_path:
            return ""
        
        from pathlib import Path
        db_path = self.project_path / "world.db"
        if not db_path.exists():
            return ""
        
        try:
            # Build query from entity name and key terms
            query = f"{stub.name} {stub.description or ''}"
            if text:
                # Extract key terms from text (first 200 chars)
                key_terms = text[:200]
                query += " " + key_terms
            
            # Search for similar historical facts
            historical_facts = self.memory_service.search(query, limit=5)
            
            if not historical_facts:
                return ""
            
            # Build briefing
            briefing = "## Historical Context\n\n"
            briefing += "The following information was found in previous reports:\n\n"
            
            for i, fact in enumerate(historical_facts, 1):
                briefing += f"{i}. {fact.text} (similarity: {fact.score:.2f})\n"
            
            briefing += "\nCompare the current report to the historical data above. "
            briefing += "Note any changes in status, location, or attributes.\n\n"
            
            return briefing
            
        except Exception as e:
            logger.warning(f"Failed to retrieve historical context: {e}")
            return ""
    
    def _build_entity(self, stub: EntityStub, resources: dict) -> Entity:
        """Convert Stub + Resources -> Full Entity."""
        
        descriptor = DescriptorComponent(
            name=stub.name,
            entity_type=stub.entity_type,
            bio=stub.description,
            aliases=stub.aliases,
            tags=stub.tags
        )
        
        # Ensure resources is a dict (handle case where it might be a list)
        if not isinstance(resources, dict):
            logger.warning(f"Resources is not a dict (type: {type(resources)}), converting to empty dict")
            resources = {}
        
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

        # Handle ID generation
        # If stub ID is temporary (stub_), we let the Entity default factory generate a new proper ID.
        # If stub ID looks persistent (e.g. from existing data), we keep it.
        entity_id = stub.id
        if entity_id.startswith("stub_"):
            # Passing None to pydantic model's id field might be tricky if it has a default factory
            # but expects a value if provided.
            # Best approach: Don't pass 'id' kwarg if we want default generation.
            
            # Use factory methods without id argument to trigger default_factory
            if stub.entity_type == EntityType.ACTOR:
                return Actor(descriptor=descriptor, state=state, spatial=spatial)
            elif stub.entity_type == EntityType.POLITY:
                return Polity(descriptor=descriptor, state=state, spatial=spatial)
            elif stub.entity_type == EntityType.LOCATION:
                return Location(descriptor=descriptor, state=state, spatial=spatial)
            else:
                return Entity(descriptor=descriptor, state=state, spatial=spatial)
        
        # Factory with explicit ID
        if stub.entity_type == EntityType.ACTOR:
            return Actor(id=entity_id, descriptor=descriptor, state=state, spatial=spatial)
        elif stub.entity_type == EntityType.POLITY:
            return Polity(id=entity_id, descriptor=descriptor, state=state, spatial=spatial)
        elif stub.entity_type == EntityType.LOCATION:
            return Location(id=entity_id, descriptor=descriptor, state=state, spatial=spatial)
        else:
            return Entity(id=entity_id, descriptor=descriptor, state=state, spatial=spatial)
