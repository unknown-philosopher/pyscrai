"""Narrative Synthesis Service Tests.

Tests for the NarrativeSynthesisService that generates narratives from knowledge graphs.
"""

import asyncio
import unittest
import tempfile
import os
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import duckdb

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.domain.intelligence.narrative_service import NarrativeSynthesisService
from forge.infrastructure.llm.base import LLMProvider
from forge.infrastructure.llm.models import ModelInfo, ModelPricing


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self):
        self.provider_name_value = "mock"
        self.default_model = "test-model"
        self._complete_responses: Dict[str, dict] = {}
        self._list_models_response: List[ModelInfo] = [
            ModelInfo(
                id="test-model",
                name="Test Model",
                description="Test model for testing",
                context_length=4096,
                pricing=ModelPricing(prompt=0.0, completion=0.0),
            )
        ]
    
    @property
    def provider_name(self) -> str:
        return self.provider_name_value
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict:
        """Mock complete method."""
        # Default narrative response
        response = {
            "choices": [{
                "message": {
                    "content": """# Narrative

This document describes relationships between entities.

## KEY ENTITIES

- Entity1: Important entity
- Entity2: Another important entity

## EVIDENCE CHAIN

Entity1 → WORKS_AT → Entity2"""
                }
            }]
        }
        return self._complete_responses.get(model, response)
    
    async def stream_complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ):
        """Mock stream complete (not used in tests)."""
        yield ""
    
    async def list_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """Mock list models."""
        return self._list_models_response
    
    async def get_model(self, model_id: str) -> ModelInfo | None:
        """Mock get model."""
        for model in self._list_models_response:
            if model.id == model_id:
                return model
        return None
    
    async def close(self) -> None:
        """Mock close."""
        pass


class NarrativeSynthesisServiceTest(unittest.IsolatedAsyncioTestCase):
    """Test NarrativeSynthesisService functionality."""
    
    async def asyncSetUp(self) -> None:
        """Set up test fixtures with temporary database."""
        self.bus = EventBus()
        self.llm_provider = MockLLMProvider()
        self.temp_db_path = tempfile.mktemp(suffix='.duckdb')
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
        self.db_conn = duckdb.connect(self.temp_db_path)
        self._create_schema()
        self.narrative_service = NarrativeSynthesisService(
            self.bus,
            self.llm_provider,
            self.db_conn
        )
        await self.narrative_service.start()
    
    def _create_schema(self):
        """Create database schema for testing."""
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id VARCHAR PRIMARY KEY,
                type VARCHAR NOT NULL,
                label VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY,
                source VARCHAR NOT NULL,
                target VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                confidence DOUBLE NOT NULL,
                doc_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db_conn.commit()
    
    def _insert_test_entity(self, entity_id: str, entity_type: str, label: str):
        """Insert a test entity."""
        self.db_conn.execute("""
            INSERT OR REPLACE INTO entities (id, type, label)
            VALUES (?, ?, ?)
        """, (entity_id, entity_type, label))
        self.db_conn.commit()
    
    def _insert_test_relationship(
        self,
        source: str,
        target: str,
        rel_type: str,
        confidence: float,
        doc_id: str
    ):
        """Insert a test relationship."""
        self.db_conn.execute("""
            INSERT INTO relationships (source, target, type, confidence, doc_id)
            VALUES (?, ?, ?, ?, ?)
        """, (source, target, rel_type, confidence, doc_id))
        self.db_conn.commit()
    
    async def asyncTearDown(self) -> None:
        """Clean up test fixtures."""
        if self.db_conn:
            self.db_conn.close()
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
        wal_file = self.temp_db_path + '.wal'
        if os.path.exists(wal_file):
            os.unlink(wal_file)
    
    async def test_narrative_service_subscribes_to_events(self) -> None:
        """Test that narrative service subscribes to graph updated events."""
        narrative_events: list[EventPayload] = []
        
        async def on_narrative(payload: EventPayload) -> None:
            narrative_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_NARRATIVE_GENERATED, on_narrative)
        
        # Publish graph updated event
        await self.bus.publish(
            events.TOPIC_GRAPH_UPDATED,
            {
                "doc_id": "test_doc",
                "graph_stats": {
                    "node_count": 2,
                    "edge_count": 1,
                    "nodes": [
                        {"id": "Alice", "type": "PERSON", "label": "Alice"},
                        {"id": "CompanyA", "type": "ORG", "label": "CompanyA"},
                    ],
                    "edges": [{
                        "source": "Alice",
                        "target": "CompanyA",
                        "type": "WORKS_AT",
                        "confidence": 0.9,
                        "doc_id": "test_doc",
                    }],
                }
            }
        )
        
        await asyncio.sleep(0.5)
        
        # Should have generated a narrative
        self.assertGreater(len(narrative_events), 0)
        self.assertEqual(narrative_events[0]["doc_id"], "test_doc")
        self.assertIn("narrative", narrative_events[0])
    
    async def test_narrative_generates_from_graph_stats(self) -> None:
        """Test that narrative service generates narrative from graph stats."""
        narrative_events: list[EventPayload] = []
        
        async def on_narrative(payload: EventPayload) -> None:
            narrative_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_NARRATIVE_GENERATED, on_narrative)
        
        graph_stats = {
            "node_count": 3,
            "edge_count": 2,
            "nodes": [
                {"id": "Bob", "type": "PERSON", "label": "Bob"},
                {"id": "CompanyB", "type": "ORG", "label": "CompanyB"},
                {"id": "CityC", "type": "LOCATION", "label": "CityC"},
            ],
            "edges": [
                {
                    "source": "Bob",
                    "target": "CompanyB",
                    "type": "WORKS_AT",
                    "confidence": 0.85,
                    "doc_id": "test_doc_2",
                },
                {
                    "source": "CompanyB",
                    "target": "CityC",
                    "type": "LOCATED_IN",
                    "confidence": 0.9,
                    "doc_id": "test_doc_2",
                },
            ],
        }
        
        narrative = await self.narrative_service.generate_narrative("test_doc_2", graph_stats)
        
        # Verify narrative was generated
        self.assertIsNotNone(narrative)
        self.assertIsInstance(narrative, str)
        self.assertGreater(len(narrative), 0)
        
        # Verify event was published
        await asyncio.sleep(0.3)
        self.assertGreater(len(narrative_events), 0)
        self.assertEqual(narrative_events[0]["doc_id"], "test_doc_2")
        self.assertEqual(narrative_events[0]["narrative"], narrative)
    
    async def test_narrative_generates_from_database(self) -> None:
        """Test that narrative service generates narrative from database."""
        # Insert test data
        self._insert_test_entity("Charlie", "PERSON", "Charlie")
        self._insert_test_entity("CompanyC", "ORG", "CompanyC")
        self._insert_test_relationship("Charlie", "CompanyC", "WORKS_AT", 0.9, "test_doc_3")
        
        narrative = await self.narrative_service.generate_narrative("test_doc_3")
        
        # Verify narrative was generated
        self.assertIsNotNone(narrative)
        self.assertIsInstance(narrative, str)
    
    async def test_narrative_caches_results(self) -> None:
        """Test that narrative service caches generated narratives."""
        graph_stats = {
            "node_count": 1,
            "edge_count": 0,
            "nodes": [{"id": "Dave", "type": "PERSON", "label": "Dave"}],
            "edges": [],
        }
        
        # Generate narrative twice
        narrative1 = await self.narrative_service.generate_narrative("test_doc_4", graph_stats)
        narrative2 = await self.narrative_service.generate_narrative("test_doc_4", graph_stats)
        
        # Should return same narrative (cached)
        self.assertEqual(narrative1, narrative2)
    
    async def test_narrative_handles_empty_graph(self) -> None:
        """Test that narrative service handles empty graphs gracefully."""
        graph_stats = {
            "node_count": 0,
            "edge_count": 0,
            "nodes": [],
            "edges": [],
        }
        
        narrative = await self.narrative_service.generate_narrative("test_doc_empty", graph_stats)
        
        # Should return None for empty graph
        self.assertIsNone(narrative)
    
    async def test_narrative_handles_missing_document(self) -> None:
        """Test that narrative service handles missing documents gracefully."""
        narrative = await self.narrative_service.generate_narrative("non_existent_doc")
        
        # Should return None if no data found
        self.assertIsNone(narrative)
    
    async def test_narrative_handles_llm_error(self) -> None:
        """Test that narrative service handles LLM errors gracefully."""
        # Make LLM provider raise an error
        async def failing_complete(*args, **kwargs):
            raise Exception("LLM error")
        
        self.llm_provider.complete = failing_complete
        
        graph_stats = {
            "node_count": 1,
            "edge_count": 0,
            "nodes": [{"id": "Eve", "type": "PERSON", "label": "Eve"}],
            "edges": [],
        }
        
        # Should return None on LLM error
        narrative = await self.narrative_service.generate_narrative("test_doc_error", graph_stats)
        self.assertIsNone(narrative)
    
    async def test_narrative_emits_agui_events(self) -> None:
        """Test that narrative service emits AG-UI events."""
        agui_events: list[EventPayload] = []
        
        async def on_agui(payload: EventPayload) -> None:
            agui_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_AGUI_EVENT, on_agui)
        
        graph_stats = {
            "node_count": 2,
            "edge_count": 1,
            "nodes": [
                {"id": "Frank", "type": "PERSON", "label": "Frank"},
                {"id": "CompanyF", "type": "ORG", "label": "CompanyF"},
            ],
            "edges": [{
                "source": "Frank",
                "target": "CompanyF",
                "type": "WORKS_AT",
                "confidence": 0.9,
                "doc_id": "test_doc_agui",
            }],
        }
        
        await self.narrative_service.generate_narrative("test_doc_agui", graph_stats)
        
        await asyncio.sleep(0.3)
        
        # Should have emitted AG-UI event
        self.assertGreater(len(agui_events), 0)
        self.assertIn("message", agui_events[0])
    
    async def test_narrative_includes_entity_and_relationship_counts(self) -> None:
        """Test that narrative event includes entity and relationship counts."""
        narrative_events: list[EventPayload] = []
        
        async def on_narrative(payload: EventPayload) -> None:
            narrative_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_NARRATIVE_GENERATED, on_narrative)
        
        graph_stats = {
            "node_count": 5,
            "edge_count": 3,
            "nodes": [
                {"id": f"Entity{i}", "type": "PERSON", "label": f"Entity{i}"}
                for i in range(5)
            ],
            "edges": [
                {
                    "source": f"Entity{i}",
                    "target": f"Entity{i+1}",
                    "type": "KNOWS",
                    "confidence": 0.8,
                    "doc_id": "test_doc_counts",
                }
                for i in range(3)
            ],
        }
        
        await self.narrative_service.generate_narrative("test_doc_counts", graph_stats)
        
        await asyncio.sleep(0.3)
        
        # Verify event includes counts
        self.assertGreater(len(narrative_events), 0)
        event = narrative_events[0]
        self.assertEqual(event["entity_count"], 5)
        self.assertEqual(event["relationship_count"], 3)


if __name__ == "__main__":
    unittest.main()
