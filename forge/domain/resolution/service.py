"""Entity Resolution Service for PyScrAI Forge.

Processes extracted entities, performs deduplication, and identifies relationships.
"""

import asyncio
from typing import Dict, List, Any
from forge.core.event_bus import EventBus, EventPayload
from forge.core import events


class EntityResolutionService:
    """Resolves entities and discovers relationships between them."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._entity_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def start(self):
        """Start the service by subscribing to entity extraction events."""
        await self.event_bus.subscribe(
            events.TOPIC_ENTITY_EXTRACTED, 
            self.handle_entity_extracted
        )
    
    async def handle_entity_extracted(self, payload: EventPayload):
        """Process extracted entities and identify relationships."""
        doc_id = payload.get("doc_id", "unknown")
        entities = payload.get("entities", [])
        
        # Cache entities by document
        self._entity_cache[doc_id] = entities
        
        # Simulate relationship detection (replace with real logic later)
        await asyncio.sleep(0.3)
        
        relationships = []
        
        # Simple pattern: if we have PERSON and ORG in same doc, create relationship
        persons = [e for e in entities if e.get("type") == "PERSON"]
        orgs = [e for e in entities if e.get("type") == "ORG"]
        
        for person in persons:
            for org in orgs:
                relationships.append({
                    "source": person.get("text"),
                    "source_type": "PERSON",
                    "target": org.get("text"),
                    "target_type": "ORG",
                    "relation_type": "WORKS_AT",
                    "confidence": 0.85,
                })
        
        if relationships:
            await self.event_bus.publish(
                events.TOPIC_RELATIONSHIP_FOUND,
                events.create_relationship_found_event(
                    doc_id=doc_id,
                    relationships=relationships,
                )
            )
