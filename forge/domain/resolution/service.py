"""Entity Resolution Service for PyScrAI Forge.

Processes extracted entities, performs deduplication, and identifies relationships using LLM.
"""

import asyncio
import logging
from collections import defaultdict
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
        """Process extracted entities and identify relationships using LLM.
        
        Uses Strategy 6 (Hybrid Approach) for large entity sets:
        - Small sets (<=15 entities): Process normally
        - Large sets (>15 entities): Batched parallel processing with progressive publishing
        """
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
        
        if len(entities) <= 15:
            # Small set: process normally
            relationships = await self._extract_relationships(doc_id, entities, document_content)
            if relationships:
                await self._publish_relationships(doc_id, relationships, is_complete=True)
                logger.info(f"Extracted {len(relationships)} relationships from document {doc_id}")
            else:
                logger.info(f"No relationships found in document {doc_id}")
        else:
            # Large set: use batched parallel processing
            logger.info(f"Processing {len(entities)} entities using batched parallel approach for document {doc_id}")
            await self._extract_relationships_batched(doc_id, entities, document_content)
    
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
            max_tokens=8000,
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
    
    def _create_smart_batches(
        self, 
        entities: List[Dict[str, Any]], 
        batch_size: int = 12
    ) -> List[List[Dict[str, Any]]]:
        """Create smart batches by grouping entities by type before batching.
        
        This improves relationship detection accuracy by keeping related entities
        (same type) together in the same batch.
        
        Args:
            entities: List of entity dictionaries
            batch_size: Target size for each batch (default: 12)
            
        Returns:
            List of entity batches
        """
        # Group entities by type
        type_groups = defaultdict(list)
        for entity in entities:
            entity_type = entity.get("type", "UNKNOWN")
            type_groups[entity_type].append(entity)
        
        # Create batches prioritizing same-type relationships
        batches = []
        current_batch = []
        
        # First, try to fill batches with same-type entities
        for entity_type, type_entities in type_groups.items():
            for entity in type_entities:
                if len(current_batch) >= batch_size:
                    batches.append(current_batch)
                    current_batch = []
                current_batch.append(entity)
        
        # Add remaining entities to batches
        if current_batch:
            batches.append(current_batch)
        
        # If we have very few batches, try to balance them better
        if len(batches) == 1 and len(entities) > batch_size:
            # Redistribute into multiple batches
            batches = [
                entities[i:i + batch_size] 
                for i in range(0, len(entities), batch_size)
            ]
        
        logger.debug(f"Created {len(batches)} batches from {len(entities)} entities")
        return batches
    
    async def _extract_relationships_batch(
        self,
        doc_id: str,
        batch: List[Dict[str, Any]],
        document_content: str,
        batch_idx: int
    ) -> List[Dict[str, Any]]:
        """Extract relationships for a single batch of entities.
        
        Args:
            doc_id: Document ID
            batch: List of entities in this batch
            document_content: Original document content for context
            batch_idx: Index of this batch (for logging)
            
        Returns:
            List of relationship dictionaries for this batch
        """
        try:
            logger.debug(f"Processing batch {batch_idx} with {len(batch)} entities for document {doc_id}")
            relationships = await self._extract_relationships(doc_id, batch, document_content)
            logger.debug(f"Batch {batch_idx} found {len(relationships)} relationships")
            return relationships
        except Exception as e:
            logger.error(f"Error processing batch {batch_idx} for document {doc_id}: {e}", exc_info=True)
            return []
    
    async def _extract_relationships_batched(
        self,
        doc_id: str,
        entities: List[Dict[str, Any]],
        document_content: str
    ) -> List[Dict[str, Any]]:
        """Extract relationships using batched parallel processing with progressive publishing.
        
        Implements Strategy 6 (Hybrid Approach):
        - Smart batching by entity type
        - Parallel processing with asyncio.gather
        - Progressive publishing as batches complete
        
        Args:
            doc_id: Document ID
            entities: List of all entities to process
            document_content: Original document content for context
            
        Returns:
            List of all relationship dictionaries found
        """
        # Create smart batches by type
        batches = self._create_smart_batches(entities, batch_size=12)
        
        if not batches:
            logger.warning(f"No batches created for document {doc_id}")
            return []
        
        logger.info(f"Processing {len(batches)} batches in parallel for document {doc_id}")
        
        # Process batches in parallel
        tasks = [
            self._extract_relationships_batch(doc_id, batch, document_content, batch_idx)
            for batch_idx, batch in enumerate(batches)
        ]
        
        # Gather results (with error handling)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Publish incrementally and collect all relationships
        all_relationships = []
        for batch_idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch {batch_idx} failed for document {doc_id}: {result}", exc_info=True)
            else:
                batch_relationships = result
                if batch_relationships:
                    all_relationships.extend(batch_relationships)
                    # Publish this batch's relationships immediately
                    await self._publish_relationships(
                        doc_id, 
                        batch_relationships,
                        batch_index=batch_idx,
                        is_complete=(batch_idx == len(batches) - 1)
                    )
                    logger.debug(
                        f"Published batch {batch_idx} with {len(batch_relationships)} relationships "
                        f"(complete={batch_idx == len(batches) - 1})"
                    )
        
        logger.info(
            f"Completed batched processing for document {doc_id}: "
            f"{len(all_relationships)} total relationships from {len(batches)} batches"
        )
        return all_relationships
    
    async def _publish_relationships(
        self,
        doc_id: str,
        relationships: List[Dict[str, Any]],
        batch_index: Optional[int] = None,
        is_complete: bool = True
    ) -> None:
        """Publish relationships to the event bus.
        
        Args:
            doc_id: Document ID
            relationships: List of relationship dictionaries
            batch_index: Optional batch index for incremental publishing
            is_complete: Whether this is the final batch
        """
        if not relationships:
            return
        
        await self.event_bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id=doc_id,
                relationships=relationships,
                batch_index=batch_index,
                is_complete=is_complete
            )
        )