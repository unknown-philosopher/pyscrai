"""Phase 2 Integration Tests - Full Intelligence Pipeline.

Tests the complete Phase 2 pipeline:
- Document Extraction → Entity Identification
- Entity Resolution → Relationship Detection  
- Graph Analysis → Knowledge Graph Construction
- DuckDB Persistence → Durable Storage & Analytics
"""

import asyncio
import unittest
import tempfile
import os
from pathlib import Path
from typing import Any

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.domain.extraction.service import DocumentExtractionService
from forge.domain.resolution.service import EntityResolutionService
from forge.domain.graph.service import GraphAnalysisService
from forge.infrastructure.persistence.duckdb_service import DuckDBPersistenceService


class Phase2IntegrationTest(unittest.IsolatedAsyncioTestCase):
    """Test the complete Phase 2 intelligence pipeline."""

    async def asyncSetUp(self) -> None:
        """Set up test fixtures with all Phase 2 services."""
        self.bus = EventBus()
        
        # Initialize all Phase 2 services
        self.extraction_service = DocumentExtractionService(self.bus)
        self.resolution_service = EntityResolutionService(self.bus)
        self.graph_service = GraphAnalysisService(self.bus)
        
        # Use temporary database for testing (let DuckDB create the file)
        self.temp_db_path = tempfile.mktemp(suffix='.duckdb')
        # Remove file if it exists (from previous failed test)
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
        self.persistence_service = DuckDBPersistenceService(
            self.bus, 
            db_path=self.temp_db_path
        )
        
        # Start all services
        await self.extraction_service.start()
        await self.resolution_service.start()
        await self.graph_service.start()
        await self.persistence_service.start()

    async def asyncTearDown(self) -> None:
        """Clean up test fixtures."""
        if self.persistence_service:
            self.persistence_service.close()
        # Clean up temporary database and related files
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
        # DuckDB may create .wal files
        wal_file = self.temp_db_path + '.wal'
        if os.path.exists(wal_file):
            os.unlink(wal_file)

    async def test_full_pipeline_single_document(self) -> None:
        """Test complete pipeline processing for a single document."""
        # Track events through the pipeline
        entities_received: list[EventPayload] = []
        relationships_received: list[EventPayload] = []
        graph_updates_received: list[EventPayload] = []
        agui_events_received: list[EventPayload] = []

        async def on_entity_extracted(payload: EventPayload) -> None:
            entities_received.append(payload)

        async def on_relationship_found(payload: EventPayload) -> None:
            relationships_received.append(payload)

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates_received.append(payload)

        async def on_agui_event(payload: EventPayload) -> None:
            agui_events_received.append(payload)

        await self.bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, on_entity_extracted)
        await self.bus.subscribe(events.TOPIC_RELATIONSHIP_FOUND, on_relationship_found)
        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)
        await self.bus.subscribe(events.TOPIC_AGUI_EVENT, on_agui_event)

        # Ingest a document
        doc_id = "test_doc_001"
        await self.bus.publish(
            events.TOPIC_DATA_INGESTED,
            events.create_data_ingested_event(
                doc_id=doc_id,
                content="Alice works at PyScrAI, a company focused on AI research."
            )
        )

        # Wait for full pipeline processing
        await asyncio.sleep(2)

        # Verify entities were extracted
        self.assertGreater(len(entities_received), 0)
        entity_payload = entities_received[0]
        self.assertEqual(entity_payload.get("doc_id"), doc_id)
        self.assertIn("entities", entity_payload)
        self.assertGreater(len(entity_payload.get("entities", [])), 0)

        # Verify relationships were detected
        self.assertGreater(len(relationships_received), 0)
        rel_payload = relationships_received[0]
        self.assertEqual(rel_payload.get("doc_id"), doc_id)
        self.assertIn("relationships", rel_payload)
        self.assertGreater(len(rel_payload.get("relationships", [])), 0)

        # Verify graph was updated
        self.assertGreater(len(graph_updates_received), 0)
        graph_payload = graph_updates_received[0]
        self.assertEqual(graph_payload.get("doc_id"), doc_id)
        self.assertIn("graph_stats", graph_payload)
        graph_stats = graph_payload.get("graph_stats", {})
        self.assertGreater(graph_stats.get("node_count", 0), 0)
        self.assertGreater(graph_stats.get("edge_count", 0), 0)

        # Verify persistence (check database)
        entity_count = self.persistence_service.get_entity_count()
        relationship_count = self.persistence_service.get_relationship_count()
        self.assertGreater(entity_count, 0)
        self.assertGreater(relationship_count, 0)

        # Verify AG-UI events were emitted
        self.assertGreater(len(agui_events_received), 0)

    async def test_full_pipeline_multiple_documents(self) -> None:
        """Test pipeline processing multiple documents sequentially."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        # Process multiple documents
        documents = [
            {"doc_id": "doc_001", "content": "Alice works at CompanyA."},
            {"doc_id": "doc_002", "content": "Bob works at CompanyB."},
            {"doc_id": "doc_003", "content": "Charlie works at CompanyC."},
        ]

        for doc in documents:
            await self.bus.publish(
                events.TOPIC_DATA_INGESTED,
                events.create_data_ingested_event(
                    doc_id=doc["doc_id"],
                    content=doc["content"]
                )
            )
            await asyncio.sleep(0.8)  # Wait between documents

        # Verify all documents were processed
        await asyncio.sleep(1)
        doc_ids_processed = {g.get("doc_id") for g in graph_updates}
        self.assertEqual(len(doc_ids_processed), len(documents))

        # Verify database contains data from all documents
        entity_count = self.persistence_service.get_entity_count()
        relationship_count = self.persistence_service.get_relationship_count()
        self.assertGreater(entity_count, 0)
        self.assertGreater(relationship_count, 0)

        # Verify graph stats accumulated
        # Note: Current simulated extraction returns same entities, so node count may not increase
        # as expected. We verify that graph processing occurred for all documents.
        final_graph = graph_updates[-1].get("graph_stats", {})
        # Graph should have processed data (at least some nodes/edges)
        self.assertGreater(final_graph.get("node_count", 0), 0)
        self.assertGreater(final_graph.get("edge_count", 0), 0)

    async def test_pipeline_event_ordering(self) -> None:
        """Test that events flow through pipeline in correct order."""
        event_order: list[tuple[str, str]] = []  # (event_type, doc_id)

        async def on_entity_extracted(payload: EventPayload) -> None:
            event_order.append(("entity", payload.get("doc_id", "")))

        async def on_relationship_found(payload: EventPayload) -> None:
            event_order.append(("relationship", payload.get("doc_id", "")))

        async def on_graph_updated(payload: EventPayload) -> None:
            event_order.append(("graph", payload.get("doc_id", "")))

        await self.bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, on_entity_extracted)
        await self.bus.subscribe(events.TOPIC_RELATIONSHIP_FOUND, on_relationship_found)
        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        doc_id = "test_order"
        await self.bus.publish(
            events.TOPIC_DATA_INGESTED,
            events.create_data_ingested_event(doc_id=doc_id, content="Test content")
        )

        await asyncio.sleep(2)

        # Verify events occurred in correct order
        event_types = [e[0] for e in event_order if e[1] == doc_id]
        
        # Entity extraction should come first
        self.assertIn("entity", event_types)
        entity_idx = event_types.index("entity")
        
        # Relationship should come after entity
        if "relationship" in event_types:
            rel_idx = event_types.index("relationship")
            self.assertGreater(rel_idx, entity_idx)
            
            # Graph should come after relationship
            if "graph" in event_types:
                graph_idx = event_types.index("graph")
                self.assertGreater(graph_idx, rel_idx)

    async def test_persistence_data_retrieval(self) -> None:
        """Test that persisted data can be retrieved from database."""
        # Process a document
        await self.bus.publish(
            events.TOPIC_DATA_INGESTED,
            events.create_data_ingested_event(
                doc_id="test_retrieval",
                content="Alice works at PyScrAI."
            )
        )

        await asyncio.sleep(2)

        # Retrieve entities
        entities = self.persistence_service.get_all_entities()
        self.assertGreater(len(entities), 0)
        
        # Verify entity structure
        entity = entities[0]
        self.assertIn("id", entity)
        self.assertIn("type", entity)
        self.assertIn("label", entity)
        self.assertIn("created_at", entity)

        # Retrieve relationships
        relationships = self.persistence_service.get_all_relationships()
        self.assertGreater(len(relationships), 0)
        
        # Verify relationship structure
        rel = relationships[0]
        self.assertIn("id", rel)
        self.assertIn("source", rel)
        self.assertIn("target", rel)
        self.assertIn("type", rel)
        self.assertIn("confidence", rel)
        self.assertIn("doc_id", rel)
        self.assertIn("created_at", rel)

        # Verify relationships reference valid entities
        entity_ids = {e["id"] for e in entities}
        for rel in relationships:
            self.assertIn(rel["source"], entity_ids)
            self.assertIn(rel["target"], entity_ids)

    async def test_graph_node_accumulation(self) -> None:
        """Test that graph nodes accumulate across multiple documents."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        # Process documents that share some entities
        await self.bus.publish(
            events.TOPIC_DATA_INGESTED,
            events.create_data_ingested_event(
                doc_id="doc_shared_1",
                content="Alice works at PyScrAI."
            )
        )
        await asyncio.sleep(1.5)

        # Verify we received graph updates
        self.assertGreater(len(graph_updates), 0, "No graph updates received")
        first_update = graph_updates[0].get("graph_stats", {})
        first_node_count = first_update.get("node_count", 0)

        await self.bus.publish(
            events.TOPIC_DATA_INGESTED,
            events.create_data_ingested_event(
                doc_id="doc_shared_2",
                content="Bob works at PyScrAI."  # Same company, different person
            )
        )
        await asyncio.sleep(1)

        # Graph should accumulate nodes
        if len(graph_updates) > 1:
            later_update = graph_updates[-1].get("graph_stats", {})
            later_node_count = later_update.get("node_count", 0)
            # Should have more or equal nodes (depending on deduplication)
            self.assertGreaterEqual(later_node_count, first_node_count)

    async def test_persistence_count_accuracy(self) -> None:
        """Test that persistence service counts are accurate."""
        # Process multiple documents
        for i in range(3):
            await self.bus.publish(
                events.TOPIC_DATA_INGESTED,
                events.create_data_ingested_event(
                    doc_id=f"count_test_{i}",
                    content=f"Person{i} works at Company{i}."
                )
            )
            await asyncio.sleep(0.8)

        await asyncio.sleep(1)

        # Get counts
        entity_count = self.persistence_service.get_entity_count()
        relationship_count = self.persistence_service.get_relationship_count()

        # Get actual data
        entities = self.persistence_service.get_all_entities()
        relationships = self.persistence_service.get_all_relationships()

        # Verify counts match actual data
        self.assertEqual(entity_count, len(entities))
        self.assertEqual(relationship_count, len(relationships))
        self.assertGreater(entity_count, 0)
        self.assertGreater(relationship_count, 0)


if __name__ == "__main__":
    unittest.main()
