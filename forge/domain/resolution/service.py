"""Entity Resolution Service for PyScrAI Forge.

Processes extracted entities, performs deduplication, and identifies relationships using LLM.
"""

import logging
from typing import Dict, List, Any, Optional

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.core.services import BaseLLMService, call_llm_and_parse_json
from forge.infrastructure.llm.base import LLMProvider
from forge.config.prompts import render_prompt

logger = logging.getLogger(__name__)


class EntityResolutionService(BaseLLMService):
    """Resolves entities and discovers relationships between them using LLM analysis."""
    
    def __init__(self, event_bus: EventBus, llm_provider: Optional[LLMProvider] = None):
        """Initialize the entity resolution service.
        
        Args:
            event_bus: Event bus for publishing/subscribing to events
            llm_provider: LLM provider for relationship extraction (optional, will use default if not provided)
        """
        super().__init__(event_bus, llm_provider, "EntityResolutionService")
        self._entity_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._document_cache: Dict[str, str] = {}  # Cache document content by doc_id
    
    async def start(self):
        """Start the service by subscribing to events."""
        # Subscribe to document ingestion to cache content
        await self.event_bus.subscribe(
            events.TOPIC_DATA_INGESTED,
            self.handle_data_ingested
        )
        # Subscribe to entity extraction to extract relationships
        await self.event_bus.subscribe(
            events.TOPIC_ENTITY_EXTRACTED, 
            self.handle_entity_extracted
        )
    
    async def handle_data_ingested(self, payload: EventPayload):
        """Cache document content for relationship extraction."""
        doc_id = payload.get("doc_id", "unknown")
        content = payload.get("content", "")
        if content:
            self._document_cache[doc_id] = content
    
    async def handle_entity_extracted(self, payload: EventPayload):
        """Process extracted entities and identify relationships using LLM."""
        doc_id = payload.get("doc_id", "unknown")
        entities = payload.get("entities", [])
        
        if not entities:
            logger.warning(f"No entities extracted from document {doc_id}")
            return
        
        # Cache entities by document
        self._entity_cache[doc_id] = entities
        
        # Get document content for context
        document_content = self._document_cache.get(doc_id, "")
        if not document_content:
            logger.warning(f"No document content cached for {doc_id}, relationship extraction may be less accurate")
        
        # Extract relationships using LLM
        relationships = await self._extract_relationships(doc_id, entities, document_content)
        
        if relationships:
            await self.event_bus.publish(
                events.TOPIC_RELATIONSHIP_FOUND,
                events.create_relationship_found_event(
                    doc_id=doc_id,
                    relationships=relationships,
                )
            )
            logger.info(f"Extracted {len(relationships)} relationships from document {doc_id}")
        else:
            logger.info(f"No relationships found in document {doc_id}")
    
    async def _extract_relationships(
        self,
        doc_id: str,
        entities: List[Dict[str, Any]],
        document_content: str
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities using LLM analysis.
        
        Args:
            doc_id: Document ID
            entities: List of extracted entities
            document_content: Original document content for context
            
        Returns:
            List of relationship dictionaries
        """
        if not await self.ensure_llm_provider():
            return []
        
        if not entities:
            return []
        
        # Render prompt using Jinja2 template
        prompt = render_prompt(
            "resolution_service",
            document_content=document_content,
            entities=entities,
        )
        
        # Type assertion: ensure_llm_provider() guarantees llm_provider is not None
        assert self.llm_provider is not None, "LLM provider should be available after ensure_llm_provider()"
        llm_provider = self.llm_provider
        
        # Call LLM and parse JSON response
        relationships = await call_llm_and_parse_json(
            llm_provider=llm_provider,
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
            service_name=self.service_name,
            doc_id=doc_id
        )
        
        if relationships is None:
            return []
        
        # Validate and normalize relationships
        if not isinstance(relationships, list):
            logger.error(f"{self.service_name}: LLM returned non-list relationship data: {type(relationships)}")
            return []
        
        # Normalize relationship format and validate against entities
        entity_names = {e.get("text") for e in entities}
        normalized_relationships = []
        
        for rel in relationships:
            if not isinstance(rel, dict):
                continue
            
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            rel_type = rel.get("type", "").strip()
            confidence = rel.get("confidence", 0.5)
            
            # Validate entities exist
            if source not in entity_names:
                logger.debug(f"Skipping relationship: source '{source}' not in entity list")
                continue
            if target not in entity_names:
                logger.debug(f"Skipping relationship: target '{target}' not in entity list")
                continue
            
            # Get entity types
            source_entity = next((e for e in entities if e.get("text") == source), None)
            target_entity = next((e for e in entities if e.get("text") == target), None)
            
            if not source_entity or not target_entity:
                continue
            
            # Only include relationships with confidence >= 0.5
            if confidence < 0.5:
                logger.debug(f"Skipping low-confidence relationship: {source} -> {target} ({confidence})")
                continue
            
            normalized_relationships.append({
                "source": source,
                "source_type": source_entity.get("type", "UNKNOWN"),
                "target": target,
                "target_type": target_entity.get("type", "UNKNOWN"),
                "relation_type": rel_type.upper(),
                "confidence": float(confidence),
            })
        
        return normalized_relationships
