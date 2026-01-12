"""
SemanticProfilerService for PyScrAI Forge.

Generates semantic profiles per entity using LLM analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.infrastructure.llm.base import LLMProvider
from forge.config.prompts import render_prompt

logger = logging.getLogger(__name__)


class SemanticProfilerService:
    """Service for generating semantic profiles of entities."""
    
    def __init__(
        self,
        event_bus: EventBus,
        llm_provider: LLMProvider,
        db_connection,  # DuckDB connection
    ):
        """Initialize the semantic profiler service.
        
        Args:
            event_bus: Event bus for subscribing to events
            llm_provider: LLM provider for profile generation
            db_connection: DuckDB connection for querying entities/relationships
        """
        self.event_bus = event_bus
        self.llm_provider = llm_provider
        self.db_conn = db_connection
        
        # Cache profiles to avoid re-computation
        self._profile_cache: Dict[str, Dict[str, Any]] = {}
        
    async def start(self):
        """Start the service and subscribe to events."""
        logger.info("Starting SemanticProfilerService")
        
        # Subscribe to entity merged and graph updated events
        # Use TOPIC_GRAPH_UPDATED instead of TOPIC_RELATIONSHIP_FOUND to ensure
        # entities are persisted to the database before generating profiles
        await self.event_bus.subscribe(events.TOPIC_ENTITY_MERGED, self.handle_entity_merged)
        await self.event_bus.subscribe(events.TOPIC_GRAPH_UPDATED, self.handle_graph_updated)
        
        logger.info("SemanticProfilerService started")
    
    async def handle_entity_merged(self, payload: EventPayload):
        """Handle entity merged events by regenerating profile."""
        kept_entity = payload.get("kept_entity")
        
        if kept_entity:
            # Invalidate cache
            if kept_entity in self._profile_cache:
                del self._profile_cache[kept_entity]
            
            # Generate new profile
            await self.generate_profile(kept_entity)
    
    async def handle_graph_updated(self, payload: EventPayload):
        """Handle graph updated events by generating profiles for new entities.
        
        This is called after entities are persisted to the database, so we can
        safely query them.
        """
        graph_stats = payload.get("graph_stats", {})
        nodes = graph_stats.get("nodes", [])
        
        # Extract unique entity IDs from the graph nodes
        entity_ids = set()
        for node in nodes:
            entity_id = node.get("id")
            if entity_id:
                entity_ids.add(entity_id)
        
        # Generate profiles for all entities in the graph update
        # This ensures entities are in the database before we query them
        for entity_id in entity_ids:
            if entity_id:
                await self.generate_profile(entity_id)
    
    async def generate_profile(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Generate a semantic profile for an entity.
        
        Args:
            entity_id: Entity ID to profile
            
        Returns:
            Semantic profile dictionary or None if error
        """
        # Check cache
        if entity_id in self._profile_cache:
            return self._profile_cache[entity_id]
        
        # Get entity information from database
        entity_info = self._get_entity_info(entity_id)
        if not entity_info:
            logger.warning(f"Entity {entity_id} not found in database")
            return None
        
        # Get relationships for this entity
        relationships = self._get_entity_relationships(entity_id)
        
        # Build context for LLM
        context = self._build_profile_context(entity_info, relationships)
        
        # Generate profile using LLM
        profile = await self._generate_profile_with_llm(entity_id, context)
        
        if profile:
            # Cache the profile
            self._profile_cache[entity_id] = profile
            
            # Emit semantic profile event
            await self.event_bus.publish(
                events.TOPIC_SEMANTIC_PROFILE,
                {
                    "entity_id": entity_id,
                    "profile": profile,
                }
            )
            
            # Also publish to workspace schema for UI visualization
            await self.event_bus.publish(
                events.TOPIC_WORKSPACE_SCHEMA,
                events.create_workspace_schema_event({
                    "type": "semantic_profile",
                    "title": f"Profile: {entity_info['label']}",
                    "props": profile
                })
            )
            
            # Emit AG-UI event
            await self.event_bus.publish(
                events.TOPIC_AGUI_EVENT,
                events.create_agui_event(
                    f"📊 Generated semantic profile for {entity_info['label']}",
                    level="info"
                )
            )
        
        return profile
    
    def _get_entity_info(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity information from database."""
        if not self.db_conn:
            return None
        
        try:
            result = self.db_conn.execute("""
                SELECT id, type, label, created_at, updated_at
                FROM entities
                WHERE id = ?
            """, (entity_id,)).fetchone()
            
            if result:
                return {
                    "id": result[0],
                    "type": result[1],
                    "label": result[2],
                    "created_at": result[3],
                    "updated_at": result[4],
                }
        except Exception as e:
            logger.error(f"Error fetching entity {entity_id}: {e}")
        
        return None
    
    def _get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for an entity."""
        if not self.db_conn:
            return []
        
        try:
            # Get outgoing relationships
            outgoing = self.db_conn.execute("""
                SELECT source, target, type, confidence
                FROM relationships
                WHERE source = ?
                ORDER BY confidence DESC
                LIMIT 20
            """, (entity_id,)).fetchall()
            
            # Get incoming relationships
            incoming = self.db_conn.execute("""
                SELECT source, target, type, confidence
                FROM relationships
                WHERE target = ?
                ORDER BY confidence DESC
                LIMIT 20
            """, (entity_id,)).fetchall()
            
            relationships = []
            
            for row in outgoing:
                relationships.append({
                    "source": row[0],
                    "target": row[1],
                    "type": row[2],
                    "confidence": row[3],
                    "direction": "outgoing"
                })
            
            for row in incoming:
                relationships.append({
                    "source": row[0],
                    "target": row[1],
                    "type": row[2],
                    "confidence": row[3],
                    "direction": "incoming"
                })
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error fetching relationships for {entity_id}: {e}")
            return []
    
    def _build_profile_context(
        self,
        entity_info: Dict[str, Any],
        relationships: List[Dict[str, Any]]
    ) -> str:
        """Build context string for LLM profiling."""
        context = f"""Entity Information:
- ID: {entity_info['id']}
- Type: {entity_info['type']}
- Label: {entity_info['label']}

Relationships ({len(relationships)} total):
"""
        
        for rel in relationships[:10]:  # Show top 10
            direction = "→" if rel["direction"] == "outgoing" else "←"
            context += f"- {rel['source']} {direction} {rel['type']} {direction} {rel['target']} (confidence: {rel['confidence']:.2f})\n"
        
        return context
    
    async def _generate_profile_with_llm(
        self,
        entity_id: str,
        context: str
    ) -> Optional[Dict[str, Any]]:
        """Generate semantic profile using LLM.
        
        Args:
            entity_id: Entity ID
            context: Context information
            
        Returns:
            Profile dictionary with summary, attributes, importance, etc.
        """
        # Render prompt using Jinja2 template
        prompt = render_prompt("semantic_profiler", context=context)
        
        content = ""
        try:
            # Get available models
            models = await self.llm_provider.list_models()
            model = models[0].id if models else self.llm_provider.default_model or ""
            
            response = await self.llm_provider.complete(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                max_tokens=500,
                temperature=0.3,
            )
            
            # Parse JSON response
            content = ""
            if "choices" in response and response["choices"]:
                content = response["choices"][0].get("message", {}).get("content", "")
            profile_data = json.loads(content.strip())
            
            # Add entity_id to profile
            profile_data["entity_id"] = entity_id
            
            logger.debug(f"Generated profile for {entity_id}")
            return profile_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {content if content else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Error generating profile with LLM: {e}")
            return None
