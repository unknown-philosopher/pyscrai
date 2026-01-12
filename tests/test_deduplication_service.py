"""Deduplication Service Tests.

Tests for the DeduplicationService that identifies and merges duplicate entities.
"""

import asyncio
import unittest
import tempfile
import os
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import duckdb

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.domain.resolution.deduplication_service import DeduplicationService
from forge.infrastructure.llm.base import LLMProvider
from forge.infrastructure.llm.models import ModelInfo, ModelPricing
from forge.infrastructure.vector.qdrant_service import QdrantService


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
        # Default response - check if message contains entity IDs to determine YES/NO
        content = messages[0].get("content", "")
        # Default to YES for duplicate confirmation
        response_text = "YES"
        if "EntityA" in content and "EntityB" in content:
            # These are different entities
            response_text = "NO"
        elif "Entity1" in content and "Entity2" in content:
            # These are duplicates
            response_text = "YES"
        
        response = {
            "choices": [{
                "message": {
                    "content": response_text
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


class MockQdrantService:
    """Mock Qdrant service for testing."""
    
    def __init__(self):
        self._duplicates: List[tuple[str, str, float]] = []
    
    async def deduplicate_entities(
        self,
        similarity_threshold: float = 0.85
    ) -> List[tuple[str, str, float]]:
        """Mock deduplicate entities method."""
        # Filter by threshold
        return [
            (e1, e2, score)
            for e1, e2, score in self._duplicates
            if score >= similarity_threshold
        ]
    
    def set_duplicates(self, duplicates: List[tuple[str, str, float]]):
        """Set the duplicate pairs to return."""
        self._duplicates = duplicates


class DeduplicationServiceTest(unittest.IsolatedAsyncioTestCase):
    """Test DeduplicationService functionality."""
    
    async def asyncSetUp(self) -> None:
        """Set up test fixtures with temporary database."""
        self.bus = EventBus()
        self.llm_provider = MockLLMProvider()
        self.qdrant_service = MockQdrantService()
        self.temp_db_path = tempfile.mktemp(suffix='.duckdb')
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
        self.db_conn = duckdb.connect(self.temp_db_path)
        self._create_schema()
        self.deduplication_service = DeduplicationService(
            self.bus,
            self.qdrant_service,
            self.llm_provider,
            self.db_conn,
            similarity_threshold=0.85,
            auto_merge=False,
        )
        await self.deduplication_service.start()
    
    def _create_schema(self):
        """Create database schema for testing."""
        # Create sequence for relationship IDs
        self.db_conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS rel_seq START 1
        """)
        
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
                id INTEGER PRIMARY KEY DEFAULT nextval('rel_seq'),
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
        doc_id: str = "test_doc"
    ):
        """Insert a test relationship."""
        self.db_conn.execute("""
            INSERT INTO relationships (source, target, type, confidence, doc_id)
            VALUES (?, ?, ?, ?, ?)
        """, (source, target, rel_type, confidence, doc_id))
        self.db_conn.commit()
    
    def _get_entity_count(self) -> int:
        """Get count of entities."""
        result = self.db_conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        return result[0] if result else 0
    
    def _entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        result = self.db_conn.execute(
            "SELECT COUNT(*) FROM entities WHERE id = ?",
            (entity_id,)
        ).fetchone()
        return result[0] > 0 if result else False
    
    async def asyncTearDown(self) -> None:
        """Clean up test fixtures."""
        if self.db_conn:
            self.db_conn.close()
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
        wal_file = self.temp_db_path + '.wal'
        if os.path.exists(wal_file):
            os.unlink(wal_file)
    
    async def test_deduplication_service_subscribes_to_events(self) -> None:
        """Test that deduplication service subscribes to graph updated events."""
        merged_events: list[EventPayload] = []
        
        async def on_merged(payload: EventPayload) -> None:
            merged_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_ENTITY_MERGED, on_merged)
        
        # Set up duplicate pairs
        self.qdrant_service.set_duplicates([("Entity1", "Entity2", 0.9)])
        
        # Insert test entities
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        
        # Publish graph updated event
        await self.bus.publish(
            events.TOPIC_GRAPH_UPDATED,
            {
                "doc_id": "test_doc",
                "graph_stats": {},
            }
        )
        
        await asyncio.sleep(0.5)
        
        # Should have processed duplicates (if LLM confirms)
        # Note: Mock LLM returns YES for Entity1/Entity2, so merge should happen
        # But we need to check if merge actually happened
        await asyncio.sleep(0.3)
        # At minimum, event should be published if merge occurred
    
    async def test_deduplication_finds_duplicates_from_qdrant(self) -> None:
        """Test that deduplication service finds duplicates from Qdrant."""
        # Set up duplicate pairs
        self.qdrant_service.set_duplicates([
            ("Entity1", "Entity2", 0.9),
            ("Entity3", "Entity4", 0.88),
        ])
        
        # Insert test entities
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        self._insert_test_entity("Entity3", "ORG", "Entity3")
        self._insert_test_entity("Entity4", "ORG", "Entity4")
        
        # Run deduplication pass
        await self.deduplication_service.run_deduplication_pass()
        
        await asyncio.sleep(0.5)
        
        # Should have processed duplicates
        # Mock LLM confirms Entity1/Entity2 as duplicates (YES)
        # Check if Entity2 was merged into Entity1
    
    async def test_deduplication_merges_entities_with_llm_confirmation(self) -> None:
        """Test that deduplication service merges entities after LLM confirmation."""
        # Set up duplicate pair
        self.qdrant_service.set_duplicates([("Entity1", "Entity2", 0.9)])
        
        # Insert test entities with relationships
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        self._insert_test_entity("TargetEntity", "ORG", "TargetEntity")
        
        # Insert relationships for Entity2
        self._insert_test_relationship("Entity2", "TargetEntity", "WORKS_AT", 0.9)
        
        initial_entity_count = self._get_entity_count()
        
        # Run deduplication (auto_merge=False, so LLM confirmation needed)
        # Mock LLM returns YES for Entity1/Entity2
        await self.deduplication_service.run_deduplication_pass()
        
        await asyncio.sleep(0.5)
        
        # Entity2 should be merged into Entity1
        # Entity1 should still exist
        self.assertTrue(self._entity_exists("Entity1"))
        # Entity2 should be deleted
        self.assertFalse(self._entity_exists("Entity2"))
        
        # Entity count should decrease by 1
        final_entity_count = self._get_entity_count()
        self.assertEqual(final_entity_count, initial_entity_count - 1)
        
        # Relationships should be updated to point to Entity1
        result = self.db_conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE source = ?",
            ("Entity1",)
        ).fetchone()
        self.assertGreater(result[0] if result else 0, 0)
    
    async def test_deduplication_auto_merge_mode(self) -> None:
        """Test that deduplication service auto-merges in auto_merge mode."""
        # Create service with auto_merge=True
        auto_merge_service = DeduplicationService(
            self.bus,
            self.qdrant_service,
            self.llm_provider,
            self.db_conn,
            similarity_threshold=0.85,
            auto_merge=True,
        )
        await auto_merge_service.start()
        
        # Set up duplicate pair
        self.qdrant_service.set_duplicates([("EntityA", "EntityB", 0.9)])
        
        # Insert test entities
        self._insert_test_entity("EntityA", "PERSON", "EntityA")
        self._insert_test_entity("EntityB", "PERSON", "EntityB")
        
        initial_entity_count = self._get_entity_count()
        
        # Run deduplication (should auto-merge without LLM confirmation)
        await auto_merge_service.run_deduplication_pass()
        
        await asyncio.sleep(0.5)
        
        # EntityB should be merged into EntityA
        self.assertTrue(self._entity_exists("EntityA"))
        self.assertFalse(self._entity_exists("EntityB"))
        
        # Entity count should decrease
        final_entity_count = self._get_entity_count()
        self.assertEqual(final_entity_count, initial_entity_count - 1)
    
    async def test_deduplication_respects_similarity_threshold(self) -> None:
        """Test that deduplication service respects similarity threshold."""
        # Set up duplicate pairs with different scores
        self.qdrant_service.set_duplicates([
            ("Entity1", "Entity2", 0.9),  # Above threshold (0.85)
            ("Entity3", "Entity4", 0.8),  # Below threshold (0.85)
        ])
        
        # Insert test entities
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        self._insert_test_entity("Entity3", "PERSON", "Entity3")
        self._insert_test_entity("Entity4", "PERSON", "Entity4")
        
        initial_entity_count = self._get_entity_count()
        
        # Run deduplication with threshold 0.85
        await self.deduplication_service.run_deduplication_pass()
        
        await asyncio.sleep(0.5)
        
        # Only Entity1/Entity2 should be merged (above threshold)
        # Entity3/Entity4 should not be merged (below threshold)
        final_entity_count = self._get_entity_count()
        # Should have merged 1 pair (2 entities -> 1 entity)
        self.assertEqual(final_entity_count, initial_entity_count - 1)
        
        # Entity3 and Entity4 should still exist
        self.assertTrue(self._entity_exists("Entity3"))
        self.assertTrue(self._entity_exists("Entity4"))
    
    async def test_deduplication_skips_already_processed_pairs(self) -> None:
        """Test that deduplication service skips already processed pairs."""
        # Set up duplicate pair
        self.qdrant_service.set_duplicates([("Entity1", "Entity2", 0.9)])
        
        # Insert test entities
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        
        initial_entity_count = self._get_entity_count()
        
        # Run deduplication twice
        await self.deduplication_service.run_deduplication_pass()
        await asyncio.sleep(0.3)
        await self.deduplication_service.run_deduplication_pass()
        await asyncio.sleep(0.3)
        
        # Should only merge once (second pass should skip already processed pair)
        final_entity_count = self._get_entity_count()
        # Should have merged exactly once
        self.assertEqual(final_entity_count, initial_entity_count - 1)
    
    async def test_deduplication_emits_entity_merged_event(self) -> None:
        """Test that deduplication service emits entity merged events."""
        merged_events: list[EventPayload] = []
        
        async def on_merged(payload: EventPayload) -> None:
            merged_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_ENTITY_MERGED, on_merged)
        
        # Set up duplicate pair
        self.qdrant_service.set_duplicates([("Entity1", "Entity2", 0.9)])
        
        # Insert test entities
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        
        # Run deduplication
        await self.deduplication_service.run_deduplication_pass()
        
        await asyncio.sleep(0.5)
        
        # Should have emitted entity merged event
        self.assertGreater(len(merged_events), 0)
        event = merged_events[0]
        self.assertEqual(event["kept_entity"], "Entity1")
        self.assertEqual(event["merged_entity"], "Entity2")
    
    async def test_deduplication_emits_agui_events(self) -> None:
        """Test that deduplication service emits AG-UI events."""
        agui_events: list[EventPayload] = []
        
        async def on_agui(payload: EventPayload) -> None:
            agui_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_AGUI_EVENT, on_agui)
        
        # Set up duplicate pairs
        self.qdrant_service.set_duplicates([
            ("Entity1", "Entity2", 0.9),
            ("Entity3", "Entity4", 0.88),
        ])
        
        # Insert test entities
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        self._insert_test_entity("Entity3", "PERSON", "Entity3")
        self._insert_test_entity("Entity4", "PERSON", "Entity4")
        
        # Run deduplication
        await self.deduplication_service.run_deduplication_pass()
        
        await asyncio.sleep(0.5)
        
        # Should have emitted AG-UI event
        self.assertGreater(len(agui_events), 0)
        self.assertIn("message", agui_events[0])
    
    async def test_deduplication_handles_no_duplicates(self) -> None:
        """Test that deduplication service handles no duplicates gracefully."""
        # Set up no duplicates
        self.qdrant_service.set_duplicates([])
        
        # Insert test entities
        self._insert_test_entity("Entity1", "PERSON", "Entity1")
        self._insert_test_entity("Entity2", "PERSON", "Entity2")
        
        initial_entity_count = self._get_entity_count()
        
        # Run deduplication
        await self.deduplication_service.run_deduplication_pass()
        
        await asyncio.sleep(0.3)
        
        # Should not merge anything
        final_entity_count = self._get_entity_count()
        self.assertEqual(final_entity_count, initial_entity_count)
    
    async def test_deduplication_handles_llm_rejection(self) -> None:
        """Test that deduplication service handles LLM rejection."""
        # Make LLM provider reject duplicates
        async def reject_complete(messages, *args, **kwargs):
            return {
                "choices": [{
                    "message": {
                        "content": "NO"
                    }
                }]
            }
        
        self.llm_provider.complete = reject_complete
        
        # Set up duplicate pair
        self.qdrant_service.set_duplicates([("EntityA", "EntityB", 0.9)])
        
        # Insert test entities
        self._insert_test_entity("EntityA", "PERSON", "EntityA")
        self._insert_test_entity("EntityB", "PERSON", "EntityB")
        
        initial_entity_count = self._get_entity_count()
        
        # Run deduplication (should reject merge)
        await self.deduplication_service.run_deduplication_pass()
        
        await asyncio.sleep(0.5)
        
        # Should not merge (LLM rejected)
        final_entity_count = self._get_entity_count()
        self.assertEqual(final_entity_count, initial_entity_count)
        
        # Both entities should still exist
        self.assertTrue(self._entity_exists("EntityA"))
        self.assertTrue(self._entity_exists("EntityB"))


if __name__ == "__main__":
    unittest.main()
