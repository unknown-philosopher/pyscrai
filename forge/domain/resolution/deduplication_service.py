"""
DeduplicationService for PyScrAI Forge.

Uses Qdrant similarity search and LLM confirmation to identify and merge duplicate entities.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any, Optional

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.infrastructure.vector.qdrant_service import QdrantService
from forge.infrastructure.llm.base import LLMProvider, RateLimitError
from forge.infrastructure.llm.rate_limiter import get_rate_limiter
from forge.config.prompts import render_prompt

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Service for detecting and merging duplicate entities."""
    
    def __init__(
        self,
        event_bus: EventBus,
        qdrant_service: QdrantService,
        llm_provider: LLMProvider,
        db_connection,  # DuckDB connection
        similarity_threshold: float = 0.85,
        auto_merge: bool = False,
    ):
        """Initialize the deduplication service.
        
        Args:
            event_bus: Event bus for subscribing to events
            qdrant_service: Qdrant service for similarity search
            llm_provider: LLM provider for duplicate confirmation
            db_connection: DuckDB connection for merging entities
            similarity_threshold: Minimum similarity to consider duplicates
            auto_merge: Automatically merge duplicates without confirmation
        """
        self.event_bus = event_bus
        self.qdrant_service = qdrant_service
        self.llm_provider = llm_provider
        self.db_conn = db_connection
        self.similarity_threshold = similarity_threshold
        self.auto_merge = auto_merge
        
        # Track processed pairs to avoid re-checking
        self._processed_pairs = set()
        
    async def start(self):
        """Start the service and subscribe to events."""
        logger.info("Starting DeduplicationService")
        
        # Subscribe to graph updated events
        await self.event_bus.subscribe(events.TOPIC_GRAPH_UPDATED, self.handle_graph_updated)
        
        logger.info("DeduplicationService started")
    
    async def handle_graph_updated(self, payload: EventPayload):
        """Handle graph updated events by checking for duplicates."""
        logger.info("Checking for duplicate entities")
        
        # Find potential duplicates from Qdrant
        duplicates = await self.qdrant_service.deduplicate_entities(
            similarity_threshold=self.similarity_threshold
        )
        
        if not duplicates:
            logger.info("No duplicates found")
            return
        
        logger.info(f"Found {len(duplicates)} potential duplicate pairs")
        
        # Process each duplicate pair
        merged_count = 0
        for entity1_id, entity2_id, score in duplicates:
            # Skip if already processed
            pair = tuple(sorted([entity1_id, entity2_id]))
            if pair in self._processed_pairs:
                continue
            
            # Confirm with LLM if not auto-merging
            if not self.auto_merge:
                is_duplicate = await self._confirm_duplicate_with_llm(
                    entity1_id, entity2_id, score
                )
                if not is_duplicate:
                    self._processed_pairs.add(pair)
                    continue
            
            # Merge entities
            await self._merge_entities(entity1_id, entity2_id)
            merged_count += 1
            self._processed_pairs.add(pair)
        
        if merged_count > 0:
            logger.info(f"Merged {merged_count} duplicate entities")
            
            # Emit AG-UI event
            await self.event_bus.publish(
                events.TOPIC_AGUI_EVENT,
                events.create_agui_event(
                    f"🔄 Merged {merged_count} duplicate entities",
                    level="info"
                )
            )
    
    async def _confirm_duplicate_with_llm(
        self,
        entity1_id: str,
        entity2_id: str,
        similarity_score: float
    ) -> bool:
        """Use LLM to confirm if two entities are duplicates.
        
        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
            similarity_score: Similarity score from Qdrant
            
        Returns:
            True if entities are duplicates, False otherwise
        """
        # Render prompt using Jinja2 template
        prompt = render_prompt(
            "deduplication_service",
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            similarity_score=similarity_score,
        )
        
        try:
            # Get available models
            models = await self.llm_provider.list_models()
            model = models[0].id if models else self.llm_provider.default_model or ""
            
            # Use rate limiter for LLM call
            rate_limiter = get_rate_limiter()
            # Pass the function itself, not the coroutine, so it can be called on each retry
            async def _make_llm_call():
                return await self.llm_provider.complete(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    max_tokens=10,
                    temperature=0.0,
                )
            
            response = await rate_limiter.execute_with_retry(
                _make_llm_call,  # Pass function, not coroutine
                is_rate_limit_error=lambda e: isinstance(e, RateLimitError) or "rate limit" in str(e).lower()
            )
            
            # Extract content from response
            content = ""
            if "choices" in response and response["choices"]:
                content = response["choices"][0].get("message", {}).get("content", "")
            answer = content.strip().upper()
            is_duplicate = "YES" in answer
            
            logger.debug(f"LLM duplicate confirmation for {entity1_id} and {entity2_id}: {answer}")
            return is_duplicate
            
        except Exception as e:
            logger.error(f"Error confirming duplicate with LLM: {e}")
            # Default to not merging if LLM fails
            return False
    
    async def _merge_entities(self, entity1_id: str, entity2_id: str):
        """Merge two entities in the database.
        
        Keeps entity1, updates all relationships pointing to entity2 to point to entity1,
        then deletes entity2.
        
        Args:
            entity1_id: Entity to keep
            entity2_id: Entity to merge into entity1
        """
        if not self.db_conn:
            logger.error("No database connection available for merging")
            return
        
        try:
            # Update all relationships where entity2 is the source
            self.db_conn.execute("""
                UPDATE relationships
                SET source = ?
                WHERE source = ?
            """, (entity1_id, entity2_id))
            
            # Update all relationships where entity2 is the target
            self.db_conn.execute("""
                UPDATE relationships
                SET target = ?
                WHERE target = ?
            """, (entity1_id, entity2_id))
            
            # Delete entity2
            self.db_conn.execute("""
                DELETE FROM entities
                WHERE id = ?
            """, (entity2_id,))
            
            # Update entity1's timestamp
            self.db_conn.execute("""
                UPDATE entities
                SET updated_at = NOW()
                WHERE id = ?
            """, (entity1_id,))
            
            self.db_conn.commit()
            
            logger.info(f"Merged entity {entity2_id} into {entity1_id}")
            
            # Emit entity merged event
            await self.event_bus.publish(
                events.TOPIC_ENTITY_MERGED,
                {
                    "kept_entity": entity1_id,
                    "merged_entity": entity2_id,
                }
            )
            
        except Exception as e:
            logger.error(f"Error merging entities {entity1_id} and {entity2_id}: {e}")
            if self.db_conn:
                self.db_conn.rollback()
    
    async def run_deduplication_pass(self):
        """Manually trigger a deduplication pass."""
        logger.info("Running manual deduplication pass")
        
        # Trigger by emitting a fake graph updated event
        await self.handle_graph_updated({})
