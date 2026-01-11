"""Domain Services Concurrency Tests.

Tests for simultaneous ingestion of multiple documents (async stress test).
"""

import asyncio
import unittest
from typing import Any

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.domain.extraction.service import DocumentExtractionService
from forge.domain.resolution.service import EntityResolutionService


class DomainConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    """Test concurrent processing of multiple documents."""

    async def asyncSetUp(self) -> None:
        """Set up test fixtures."""
        self.bus = EventBus()
        self.extraction_service = DocumentExtractionService(self.bus)
        self.resolution_service = EntityResolutionService(self.bus)
        await self.extraction_service.start()
        await self.resolution_service.start()

    async def test_concurrent_document_ingestion(self) -> None:
        """Test simultaneous ingestion of multiple documents."""
        entities_received: list[EventPayload] = []
        relationships_received: list[EventPayload] = []
        entity_lock = asyncio.Lock()
        relationship_lock = asyncio.Lock()

        async def on_entity_extracted(payload: EventPayload) -> None:
            async with entity_lock:
                entities_received.append(payload)

        async def on_relationship_found(payload: EventPayload) -> None:
            async with relationship_lock:
                relationships_received.append(payload)

        await self.bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, on_entity_extracted)
        await self.bus.subscribe(events.TOPIC_RELATIONSHIP_FOUND, on_relationship_found)

        # Publish multiple documents concurrently
        num_documents = 10
        tasks = []

        for i in range(num_documents):
            doc_id = f"doc_concurrent_{i:03d}"
            content = f"Person{i} works at Company{i}."
            task = self.bus.publish(
                events.TOPIC_DATA_INGESTED,
                events.create_data_ingested_event(doc_id=doc_id, content=content)
            )
            tasks.append(task)

        # Publish all documents simultaneously
        await asyncio.gather(*tasks)

        # Wait for all processing to complete
        await asyncio.sleep(2)

        # Verify all documents were processed
        doc_ids_in_entities = {e.get("doc_id") for e in entities_received}
        self.assertEqual(len(doc_ids_in_entities), num_documents)

        # Verify each document ID appears in entities
        for i in range(num_documents):
            expected_doc_id = f"doc_concurrent_{i:03d}"
            self.assertIn(expected_doc_id, doc_ids_in_entities)

        # Verify relationships were created for all documents
        doc_ids_in_relationships = {r.get("doc_id") for r in relationships_received}
        self.assertEqual(len(doc_ids_in_relationships), num_documents)

    async def test_concurrent_stress_test(self) -> None:
        """Stress test with many concurrent documents."""
        entities_received: list[EventPayload] = []
        entity_lock = asyncio.Lock()

        async def on_entity_extracted(payload: EventPayload) -> None:
            async with entity_lock:
                entities_received.append(payload)

        await self.bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, on_entity_extracted)

        # Publish many documents concurrently
        num_documents = 50
        tasks = []

        for i in range(num_documents):
            doc_id = f"doc_stress_{i:04d}"
            content = f"Content for document {i}"
            task = self.bus.publish(
                events.TOPIC_DATA_INGESTED,
                events.create_data_ingested_event(doc_id=doc_id, content=content)
            )
            tasks.append(task)

        # Publish all documents simultaneously
        await asyncio.gather(*tasks)

        # Wait for processing (may take longer with many documents)
        await asyncio.sleep(3)

        # Verify all documents were processed
        doc_ids_in_entities = {e.get("doc_id") for e in entities_received}
        self.assertEqual(len(doc_ids_in_entities), num_documents)

        # Verify no duplicate events (each doc_id should appear once)
        entity_counts = {}
        for entity in entities_received:
            doc_id = entity.get("doc_id")
            entity_counts[doc_id] = entity_counts.get(doc_id, 0) + 1

        # Each document should have exactly one entity extraction event
        for doc_id, count in entity_counts.items():
            self.assertEqual(count, 1, f"Document {doc_id} has {count} events (expected 1)")

    async def test_concurrent_with_mixed_documents(self) -> None:
        """Test concurrent ingestion with different document types."""
        entities_received: list[EventPayload] = []
        relationships_received: list[EventPayload] = []
        entity_lock = asyncio.Lock()
        relationship_lock = asyncio.Lock()

        async def on_entity_extracted(payload: EventPayload) -> None:
            async with entity_lock:
                entities_received.append(payload)

        async def on_relationship_found(payload: EventPayload) -> None:
            async with relationship_lock:
                relationships_received.append(payload)

        await self.bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, on_entity_extracted)
        await self.bus.subscribe(events.TOPIC_RELATIONSHIP_FOUND, on_relationship_found)

        # Create different types of documents
        documents = [
            {"doc_id": "doc_with_entities_1", "content": "Alice works at CompanyA."},
            {"doc_id": "doc_with_entities_2", "content": "Bob works at CompanyB."},
            {"doc_id": "doc_empty_1", "content": "Just some text."},
            {"doc_id": "doc_with_entities_3", "content": "Charlie works at CompanyC."},
        ]

        # Publish all documents concurrently
        tasks = [
            self.bus.publish(
                events.TOPIC_DATA_INGESTED,
                events.create_data_ingested_event(doc_id=doc["doc_id"], content=doc["content"])
            )
            for doc in documents
        ]

        await asyncio.gather(*tasks)
        await asyncio.sleep(2)

        # Verify all documents were processed
        doc_ids_in_entities = {e.get("doc_id") for e in entities_received}
        self.assertEqual(len(doc_ids_in_entities), len(documents))

        # Verify event isolation (each document should maintain its doc_id)
        for entity in entities_received:
            self.assertIn(entity.get("doc_id"), [doc["doc_id"] for doc in documents])

        for relationship in relationships_received:
            self.assertIn(relationship.get("doc_id"), [doc["doc_id"] for doc in documents])

    async def test_concurrent_event_bus_stability(self) -> None:
        """Test that event bus remains stable under concurrent load."""
        events_received = 0
        event_lock = asyncio.Lock()
        errors = []

        async def handler(payload: EventPayload) -> None:
            nonlocal events_received
            try:
                # Simulate some processing
                await asyncio.sleep(0.01)
                async with event_lock:
                    events_received += 1
            except Exception as e:
                errors.append(e)

        await self.bus.subscribe("test_topic", handler)

        # Publish many events concurrently
        num_events = 100
        tasks = [
            self.bus.publish("test_topic", {"event_id": i})
            for i in range(num_events)
        ]

        await asyncio.gather(*tasks)
        await asyncio.sleep(1)  # Wait for all handlers

        # Verify all events were processed
        self.assertEqual(events_received, num_events)
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")


if __name__ == "__main__":
    unittest.main()
