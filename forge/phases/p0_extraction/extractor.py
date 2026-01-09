"""
Entity Extractor for Forge 3.0.

LLM-powered extraction of entities and relationships from text chunks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from forge.core.models.entity import Entity, EntityType
from forge.core.models.relationship import Relationship, RelationType
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.phases.p0_extraction.chunker import TextChunk
    from forge.systems.llm.base import LLMProvider
    from forge.systems.llm.models import LLMMessage

logger = get_logger("p0_extraction.extractor")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()



# ============================================================================
# Extraction Result
# ============================================================================


@dataclass
class ExtractionResult:
    """Result from extracting entities from a chunk.
    
    Attributes:
        chunk_index: Index of the source chunk
        source_name: Name of the source document
        entities: Extracted entities
        relationships: Extracted relationships
        raw_response: Raw LLM response for debugging
        error: Error message if extraction failed
    """
    
    chunk_index: int
    source_name: str
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    raw_response: str = ""
    error: str | None = None
    
    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return self.error is None
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)
    
    @property
    def relationship_count(self) -> int:
        return len(self.relationships)


# ============================================================================
# Extractor
# ============================================================================


class EntityExtractor:
    """Extracts entities and relationships from text chunks using LLM.
    
    Usage:
        extractor = EntityExtractor(llm_provider)
        result = await extractor.extract_from_chunk(chunk)
        
        if result.success:
            for entity in result.entities:
                print(f"Found: {entity.name}")
    """
    
    # Type mapping from LLM output to EntityType
    TYPE_MAP = {
        "ACTOR": EntityType.ACTOR,
        "POLITY": EntityType.POLITY,
        "LOCATION": EntityType.LOCATION,
        "REGION": EntityType.REGION,
        "RESOURCE": EntityType.RESOURCE,
        "EVENT": EntityType.EVENT,
        "ABSTRACT": EntityType.ABSTRACT,
        # Common alternatives the LLM might use
        "PERSON": EntityType.ACTOR,
        "ORGANIZATION": EntityType.POLITY,
        "FACTION": EntityType.POLITY,
        "PLACE": EntityType.LOCATION,
        "ITEM": EntityType.RESOURCE,
        "OBJECT": EntityType.RESOURCE,
        "CONCEPT": EntityType.ABSTRACT,
    }
    
    RELATION_TYPE_MAP = {
        "ALLIANCE": RelationType.ALLIANCE,
        "ALLY": RelationType.ALLIANCE,
        "ENMITY": RelationType.ENMITY,
        "ENEMY": RelationType.ENMITY,
        "TRADE": RelationType.TRADE,
        "OWNS": RelationType.OWNS,
        "OCCUPIES": RelationType.OCCUPIES,
        "KNOWS": RelationType.KNOWS,
        "INFLUENCES": RelationType.INFLUENCES,
        "COMMANDS": RelationType.COMMANDS,
        "MEMBER_OF": RelationType.MEMBER_OF,
        "MEMBER": RelationType.MEMBER_OF,
        "PARENT_OF": RelationType.PARENT_OF,
        "SIBLING_OF": RelationType.SIBLING_OF,
        "WORKS_FOR": RelationType.WORKS_FOR,
        "LOCATED_IN": RelationType.LOCATED_IN,
        "CUSTOM": RelationType.CUSTOM,
    }
    
    def __init__(
        self,
        llm_provider: "LLMProvider",
        model: str | None = None,
        max_entities_per_chunk: int = 15,
    ):
        """Initialize the extractor.
        
        Args:
            llm_provider: LLM provider for generation
            model: Model to use (default: provider's default)
            max_entities_per_chunk: Maximum entities to request per chunk
        """
        self.llm = llm_provider
        self.model = model
        self.max_entities = max_entities_per_chunk
    
    async def extract_from_chunk(
        self,
        chunk: "TextChunk",
        context: str = "",
    ) -> ExtractionResult:
        """Extract entities and relationships from a text chunk.
        
        Args:
            chunk: Text chunk to process
            context: Optional project context
            
        Returns:
            ExtractionResult with entities and relationships
        """
        from forge.systems.llm.models import LLMMessage
        
        result = ExtractionResult(
            chunk_index=chunk.index,
            source_name=chunk.source_name,
        )
        
        try:
            # Get prompts from manager
            system_prompt = _prompt_manager.get("extraction.system_prompt")
            
            # Build user prompt with Jinja2 rendering
            user_prompt_template = _prompt_manager.get("extraction.user_prompt_template")
            user_prompt = _prompt_manager.render(
                "extraction.user_prompt_template",
                source_name=chunk.source_name,
                chunk_info=f"CHUNK: {chunk.index + 1} (characters {chunk.start_char}-{chunk.end_char})",
                text_content=chunk.content,
                context=context,
            )
            
            # Build messages
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ]
            
            # Call LLM
            response = await self.llm.generate(
                messages=messages,
                model=self.model,
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=4096,
            )
            
            result.raw_response = response.content
            
            # Parse response
            parsed = self._parse_response(response.content)
            
            # Convert to entities
            result.entities = self._convert_entities(
                parsed.get("entities", []),
                chunk.source_name,
            )
            
            # Convert to relationships (need entity name -> id mapping)
            entity_name_map = {e.name.lower(): e.id for e in result.entities}
            result.relationships = self._convert_relationships(
                parsed.get("relationships", []),
                entity_name_map,
            )
            
            logger.debug(
                f"Extracted from chunk {chunk.index}: "
                f"{result.entity_count} entities, {result.relationship_count} relationships"
            )
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Extraction failed for chunk {chunk.index}: {e}")
        
        return result
    
    def _parse_response(self, content: str) -> dict:
        """Parse the LLM response as JSON.
        
        Args:
            content: Raw LLM response
            
        Returns:
            Parsed dictionary
        """
        # Try to extract JSON from response
        content = content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (code block markers)
            lines = [l for l in lines if not l.startswith("```")]
            content = "\n".join(lines)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            # Try to find JSON object in response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from response: {content[:200]}...")
    
    def _convert_entities(
        self,
        raw_entities: list[dict],
        source_name: str,
    ) -> list[Entity]:
        """Convert raw extraction data to Entity objects.
        
        Args:
            raw_entities: Raw entity dicts from LLM
            source_name: Source document name
            
        Returns:
            List of Entity objects
        """
        from forge.utils.ids import generate_entity_id
        
        entities = []
        
        for raw in raw_entities[:self.max_entities]:
            try:
                # Get entity type
                type_str = raw.get("type", "CUSTOM").upper()
                entity_type = self.TYPE_MAP.get(type_str, EntityType.CUSTOM)
                
                # Build attributes
                attributes = raw.get("attributes", {})
                attributes["extraction_confidence"] = raw.get("confidence", 0.8)
                attributes["source_document"] = source_name
                
                # Create entity
                entity = Entity(
                    id=generate_entity_id(entity_type),
                    name=raw.get("name", "Unknown"),
                    type=entity_type,
                    description=raw.get("description", ""),
                    aliases=raw.get("aliases", []),
                    attributes=attributes,
                    provenance=[source_name],
                )
                
                entities.append(entity)
                
            except Exception as e:
                logger.warning(f"Failed to convert entity: {e}")
        
        return entities
    
    def _convert_relationships(
        self,
        raw_relationships: list[dict],
        entity_name_map: dict[str, str],
    ) -> list[Relationship]:
        """Convert raw extraction data to Relationship objects.
        
        Args:
            raw_relationships: Raw relationship dicts from LLM
            entity_name_map: Mapping of lowercase entity names to IDs
            
        Returns:
            List of Relationship objects
        """
        from forge.utils.ids import generate_relationship_id
        
        relationships = []
        
        for raw in raw_relationships:
            try:
                # Look up entity IDs
                source_name = raw.get("source_name", "").lower()
                target_name = raw.get("target_name", "").lower()
                
                source_id = entity_name_map.get(source_name)
                target_id = entity_name_map.get(target_name)
                
                if not source_id or not target_id:
                    logger.debug(
                        f"Skipping relationship: unknown entities "
                        f"'{source_name}' -> '{target_name}'"
                    )
                    continue
                
                # Get relationship type
                type_str = raw.get("type", "RELATED").upper()
                rel_type = self.RELATION_TYPE_MAP.get(type_str, RelationType.RELATED)
                
                # Create relationship
                relationship = Relationship(
                    id=generate_relationship_id(),
                    source_id=source_id,
                    target_id=target_id,
                    type=rel_type,
                    description=raw.get("description", ""),
                    strength=raw.get("strength", 0.5),
                    attributes={
                        "extraction_confidence": raw.get("confidence", 0.7),
                    },
                )
                
                relationships.append(relationship)
                
            except Exception as e:
                logger.warning(f"Failed to convert relationship: {e}")
        
        return relationships
    
    async def extract_from_chunks(
        self,
        chunks: list["TextChunk"],
        context: str = "",
        progress_callback: callable = None,
    ) -> list[ExtractionResult]:
        """Extract from multiple chunks.
        
        Args:
            chunks: List of text chunks
            context: Optional project context
            progress_callback: Optional callback(chunk_index, total, result)
            
        Returns:
            List of extraction results
        """
        results = []
        total = len(chunks)
        
        for i, chunk in enumerate(chunks):
            result = await self.extract_from_chunk(chunk, context)
            results.append(result)
            
            if progress_callback:
                progress_callback(i, total, result)
        
        return results
