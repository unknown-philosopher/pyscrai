"""Test harness for DocumentExtractionService.

Simulates document ingestion and extraction pipeline.
"""
import asyncio
from forge.core.event_bus import EventBus
from forge.domain.extraction.service import DocumentExtractionService
from forge.core import events

async def print_entities(payload):
    print(f"[Test] Entity extraction result: {payload}")

async def main():
    bus = EventBus()
    extraction_service = DocumentExtractionService(bus)
    await extraction_service.start()
    await bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, print_entities)
    # Simulate document ingestion
    await bus.publish(
        events.TOPIC_DATA_INGESTED,
        events.create_data_ingested_event(doc_id="doc1", content="Alice works at PyScrAI."),
    )
    await asyncio.sleep(1)  # Wait for async extraction

if __name__ == "__main__":
    asyncio.run(main())
