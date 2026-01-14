"""
NarrativeSynthesisService for PyScrAI Forge.

Generates intelligent narratives from documents using knowledge graph context.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, List, Optional

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.infrastructure.llm.base import LLMProvider, RateLimitError
from forge.infrastructure.llm.rate_limiter import get_rate_limiter
from forge.config.prompts import render_prompt

logger = logging.getLogger(__name__)


class NarrativeSynthesisService:
    """Service for generating narratives from knowledge graphs."""
    
    def __init__(
        self,
        event_bus: EventBus,
        llm_provider: LLMProvider,
        db_connection,  # DuckDB connection
    ):
        """Initialize the narrative synthesis service.
        
        Args:
            event_bus: Event bus for subscribing to events
            llm_provider: LLM provider for narrative generation
            db_connection: DuckDB connection for querying graph data
        """
        self.event_bus = event_bus
        self.llm_provider = llm_provider
        self.db_conn = db_connection
        self.service_name = "NarrativeSynthesisService"
        
        # Cache narratives per document
        self._narrative_cache: Dict[str, str] = {}
        
    async def start(self):
        """Start the service and subscribe to events."""
        logger.info("Starting NarrativeSynthesisService")
        
        # Subscribe to graph updated events
        await self.event_bus.subscribe(events.TOPIC_GRAPH_UPDATED, self.handle_graph_updated)
        
        logger.info("NarrativeSynthesisService started")
    
    async def handle_graph_updated(self, payload: EventPayload):
        """Handle graph updated events by generating narratives."""
        doc_id = payload.get("doc_id")
        graph_stats = payload.get("graph_stats", {})
        
        # Skip if doc_id is None (e.g., during session restore - narrative should be generated per document, not globally)
        if doc_id is None:
            logger.debug("Skipping narrative generation for None doc_id (session restore)")
            return
        
        # Generate narrative for this document
        await self.generate_narrative(doc_id, graph_stats)
    
    async def generate_narrative(
        self,
        doc_id: str,
        graph_stats: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Generate a narrative for a document.
        
        Args:
            doc_id: Document ID
            graph_stats: Optional graph statistics
            
        Returns:
            Generated narrative or None if error
        """
        # Check cache
        if doc_id in self._narrative_cache:
            return self._narrative_cache[doc_id]
        
        # Get entities and relationships from graph_stats or database
        if graph_stats:
            entities = graph_stats.get("nodes", [])
            relationships = graph_stats.get("edges", [])
        else:
            entities, relationships = self._get_graph_data_from_db(doc_id)
        
        if not entities:
            logger.warning(f"No entities found for document {doc_id}")
            return None
        
        # Build context for narrative generation
        context = self._build_narrative_context(doc_id, entities, relationships)
        
        # Generate narrative using LLM
        narrative = await self._generate_narrative_with_llm(doc_id, context)
        
        if narrative:
            # Cache the narrative
            self._narrative_cache[doc_id] = narrative
            
            # Emit narrative generated event
            await self.event_bus.publish(
                events.TOPIC_NARRATIVE_GENERATED,
                {
                    "doc_id": doc_id,
                    "narrative": narrative,
                    "entity_count": len(entities),
                    "relationship_count": len(relationships),
                }
            )
            
            # Also publish to workspace schema for UI visualization
            await self.event_bus.publish(
                events.TOPIC_WORKSPACE_SCHEMA,
                events.create_workspace_schema_event({
                    "type": "narrative",
                    "title": "Document Narrative",
                    "props": {
                        "doc_id": doc_id,
                        "narrative": narrative,
                        "entity_count": len(entities),
                        "relationship_count": len(relationships),
                    }
                })
            )
            
            # Emit AG-UI event
            await self.event_bus.publish(
                events.TOPIC_AGUI_EVENT,
                events.create_agui_event(
                    f"📝 Generated narrative for document {doc_id[:8]}... ({len(entities)} entities, {len(relationships)} relationships)",
                    level="success"
                )
            )
        
        return narrative
    
    def _get_graph_data_from_db(self, doc_id: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get entities and relationships for a document from database."""
        entities = []
        relationships = []
        
        if not self.db_conn:
            return entities, relationships
        
        try:
            # Get relationships for this document
            rel_results = self.db_conn.execute("""
                SELECT DISTINCT source, target, type, confidence
                FROM relationships
                WHERE doc_id = ?
            """, (doc_id,)).fetchall()
            
            # Extract unique entities from relationships
            entity_ids = set()
            for row in rel_results:
                entity_ids.add(row[0])
                entity_ids.add(row[1])
                relationships.append({
                    "source": row[0],
                    "target": row[1],
                    "type": row[2],
                    "confidence": row[3],
                })
            
            # Get entity details
            if entity_ids:
                placeholders = ",".join(["?" for _ in entity_ids])
                entity_results = self.db_conn.execute(f"""
                    SELECT id, type, label
                    FROM entities
                    WHERE id IN ({placeholders})
                """, list(entity_ids)).fetchall()
                
                for row in entity_results:
                    entities.append({
                        "id": row[0],
                        "type": row[1],
                        "label": row[2],
                    })
        
        except Exception as e:
            logger.error(f"Error fetching graph data for document {doc_id}: {e}")
        
        return entities, relationships
    
    def _build_narrative_context(
        self,
        doc_id: str,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> str:
        """Build context string for narrative generation."""
        # Sort entities by type
        entities_by_type: Dict[str, List[str]] = {}
        for entity in entities:
            entity_type = entity.get("type", "UNKNOWN")
            label = entity.get("label", entity.get("text", entity.get("id", "")))
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(label)
        
        # Build context
        context = f"Document ID: {doc_id}\n\n"
        context += "### ENTITIES\n"
        for entity_type, labels in sorted(entities_by_type.items()):
            context += f"- {entity_type}: {', '.join(labels[:10])}\n"
        
        context += "\n### RELATIONSHIPS\n"
        for rel in relationships[:20]:  # Show top 20 relationships
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "RELATED_TO")
            confidence = rel.get("confidence", 1.0)
            context += f"- {source} → {rel_type} → {target} (confidence: {confidence:.2f})\n"
        
        return context
    
    async def _generate_narrative_with_llm(
        self,
        doc_id: str,
        context: str
    ) -> Optional[str]:
        """Generate narrative using LLM.
        
        Args:
            doc_id: Document ID
            context: Context information
            
        Returns:
            Generated narrative markdown text
        """
        # Render prompt using Jinja2 template
        prompt = render_prompt("narrative_service", context=context)
        
        try:
            # Prefer default_model over first available model
            model = self.llm_provider.default_model
            if not model:
                models = await self.llm_provider.list_models()
                model = models[0].id if models else ""
            if not model:
                logger.error(f"{self.service_name}: No model available for LLM call")
                return None
            logger.info(f"{self.service_name}: Using model '{model}' for narrative generation")
            
            # Use rate limiter for LLM call
            rate_limiter = get_rate_limiter()
            # Pass the function itself, not the coroutine, so it can be called on each retry
            async def _make_llm_call():
                return await self.llm_provider.complete(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    max_tokens=1500,
                    temperature=0.5,
                )
            
            response = await rate_limiter.execute_with_retry(
                _make_llm_call,  # Pass function, not coroutine
                is_rate_limit_error=lambda e: isinstance(e, RateLimitError) or "rate limit" in str(e).lower()
            )
            
            # Extract content from response
            narrative = ""
            if "choices" in response and response["choices"]:
                narrative = response["choices"][0].get("message", {}).get("content", "").strip()
            logger.debug(f"Generated narrative for document {doc_id}")
            return narrative
            
        except Exception as e:
            logger.error(f"Error generating narrative with LLM: {e}")
            return None
    
    async def generate_all_narratives(self):
        """Generate narratives for all documents in the database."""
        if not self.db_conn:
            logger.warning("No database connection available")
            return
        
        try:
            # Get all unique document IDs
            doc_ids = self.db_conn.execute("""
                SELECT DISTINCT doc_id
                FROM relationships
                WHERE doc_id IS NOT NULL
            """).fetchall()
            
            logger.info(f"Generating narratives for {len(doc_ids)} documents")
            
            for (doc_id,) in doc_ids:
                await self.generate_narrative(doc_id)
        
        except Exception as e:
            logger.error(f"Error generating all narratives: {e}")
