"""Document Extraction Service for PyScrAI Forge.

Simulates document parsing and extraction. Emits entity extraction events.
"""

import asyncio
from forge.core.event_bus import EventBus, EventPayload
from forge.core import events

class DocumentExtractionService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def start(self):
        await self.event_bus.subscribe(events.TOPIC_DATA_INGESTED, self.handle_data_ingested)

    async def handle_data_ingested(self, payload: EventPayload):
        # Simulate document parsing (replace with real logic later)
        await asyncio.sleep(0.5)
        doc_id = payload.get("doc_id", "unknown")
        # Simulated extraction result
        entities = [
            {"type": "PERSON", "text": "Alice"},
            {"type": "ORG", "text": "PyScrAI"},
        ]
        await self.event_bus.publish(
            events.TOPIC_ENTITY_EXTRACTED,
            {
                "doc_id": doc_id,
                "entities": entities,
            },
        )
