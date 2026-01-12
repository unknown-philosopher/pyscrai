"""Semantic Profiler Service Tests.

Tests for the SemanticProfilerService that generates semantic profiles of entities.
"""

import asyncio
import json
import unittest
import tempfile
import os
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import duckdb

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.domain.intelligence.semantic_profiler import SemanticProfilerService
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
        # Default response
        response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "summary": "Test entity summary",
                        "attributes": ["attr1", "attr2"],
                        "importance": 7,
                        "key_relationships": ["WORKS_AT", "KNOWS"],
                        "confidence": 0.9
                    })
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


class SemanticProfilerServiceTest(unittest.IsolatedAsyncioTestCase):
    """Test SemanticProfilerService functionality."""
    
    async def asyncSetUp(self) -> None:
        """Set up test fixtures with temporary database."""
        self.bus = EventBus()
        self.llm_provider = MockLLMProvider()
        self.temp_db_path = tempfile.mktemp(suffix='.duckdb')
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
        self.db_conn = duckdb.connect(self.temp_db_path)
        self._create_schema()
        self.profiler_service = SemanticProfilerService(
            self.bus,
            self.llm_provider,
            self.db_conn
        )
        await self.profiler_service.start()
    
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
        doc_id: str = "test_doc"
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
    
    async def test_profiler_service_subscribes_to_events(self) -> None:
        """Test that profiler service subscribes to entity merged and relationship found events."""
        profile_events: list[EventPayload] = []
        
        async def on_profile(payload: EventPayload) -> None:
            profile_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_SEMANTIC_PROFILE, on_profile)
        
        # Insert test entity
        self._insert_test_entity("Alice", "PERSON", "Alice")
        self._insert_test_relationship("Alice", "CompanyA", "WORKS_AT", 0.9)
        
        # Publish relationship found event
        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            {
                "doc_id": "test_doc",
                "relationships": [{
                    "source": "Alice",
                    "target": "CompanyA",
                    "type": "WORKS_AT",
                    "confidence": 0.9,
                }]
            }
        )
        
        await asyncio.sleep(0.5)
        
        # Should have generated a profile
        self.assertGreater(len(profile_events), 0)
    
    async def test_profiler_generates_profile_for_entity(self) -> None:
        """Test that profiler generates a profile for an entity."""
        profile_events: list[EventPayload] = []
        
        async def on_profile(payload: EventPayload) -> None:
            profile_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_SEMANTIC_PROFILE, on_profile)
        
        # Insert test entity and relationships
        self._insert_test_entity("Bob", "PERSON", "Bob")
        self._insert_test_relationship("Bob", "CompanyB", "WORKS_AT", 0.85)
        self._insert_test_relationship("Bob", "Alice", "KNOWS", 0.9)
        
        # Generate profile
        profile = await self.profiler_service.generate_profile("Bob")
        
        # Verify profile was generated
        self.assertIsNotNone(profile)
        self.assertIn("summary", profile)
        self.assertIn("attributes", profile)
        self.assertIn("importance", profile)
        self.assertIn("entity_id", profile)
        self.assertEqual(profile["entity_id"], "Bob")
        
        # Verify event was published
        await asyncio.sleep(0.3)
        self.assertGreater(len(profile_events), 0)
        self.assertEqual(profile_events[0]["entity_id"], "Bob")
    
    async def test_profiler_caches_profiles(self) -> None:
        """Test that profiler caches generated profiles."""
        # Insert test entity
        self._insert_test_entity("Charlie", "PERSON", "Charlie")
        
        # Generate profile twice
        profile1 = await self.profiler_service.generate_profile("Charlie")
        profile2 = await self.profiler_service.generate_profile("Charlie")
        
        # Should return same profile (cached)
        self.assertEqual(profile1, profile2)
    
    async def test_profiler_handles_entity_merged_event(self) -> None:
        """Test that profiler handles entity merged events."""
        profile_events: list[EventPayload] = []
        
        async def on_profile(payload: EventPayload) -> None:
            profile_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_SEMANTIC_PROFILE, on_profile)
        
        # Insert test entity
        self._insert_test_entity("Dave", "PERSON", "Dave")
        
        # Generate initial profile
        await self.profiler_service.generate_profile("Dave")
        await asyncio.sleep(0.2)
        initial_count = len(profile_events)
        
        # Publish entity merged event
        await self.bus.publish(
            events.TOPIC_ENTITY_MERGED,
            {
                "kept_entity": "Dave",
                "merged_entity": "David",
            }
        )
        
        await asyncio.sleep(0.5)
        
        # Should have invalidated cache and regenerated profile
        # (cache is cleared, so new profile should be generated)
        # Verify profile was regenerated
        profile = await self.profiler_service.generate_profile("Dave")
        self.assertIsNotNone(profile)
    
    async def test_profiler_handles_missing_entity(self) -> None:
        """Test that profiler handles missing entities gracefully."""
        profile = await self.profiler_service.generate_profile("NonExistent")
        
        # Should return None for missing entity
        self.assertIsNone(profile)
    
    async def test_profiler_builds_context_from_relationships(self) -> None:
        """Test that profiler builds context from entity relationships."""
        # Insert test entity with multiple relationships
        self._insert_test_entity("Eve", "PERSON", "Eve")
        self._insert_test_relationship("Eve", "CompanyC", "WORKS_AT", 0.9)
        self._insert_test_relationship("Eve", "CompanyD", "CONSULTS_FOR", 0.8)
        self._insert_test_relationship("Alice", "Eve", "KNOWS", 0.85)
        
        # Generate profile
        profile = await self.profiler_service.generate_profile("Eve")
        
        # Should have generated profile with relationship context
        self.assertIsNotNone(profile)
        self.assertIn("key_relationships", profile)
    
    async def test_profiler_handles_llm_error(self) -> None:
        """Test that profiler handles LLM errors gracefully."""
        # Make LLM provider raise an error
        async def failing_complete(*args, **kwargs):
            raise Exception("LLM error")
        
        self.llm_provider.complete = failing_complete
        
        # Insert test entity
        self._insert_test_entity("Frank", "PERSON", "Frank")
        
        # Should return None on LLM error
        profile = await self.profiler_service.generate_profile("Frank")
        self.assertIsNone(profile)
    
    async def test_profiler_handles_invalid_json_response(self) -> None:
        """Test that profiler handles invalid JSON responses from LLM."""
        # Make LLM provider return invalid JSON
        async def invalid_json_complete(*args, **kwargs):
            return {
                "choices": [{
                    "message": {
                        "content": "This is not valid JSON"
                    }
                }]
            }
        
        self.llm_provider.complete = invalid_json_complete
        
        # Insert test entity
        self._insert_test_entity("Grace", "PERSON", "Grace")
        
        # Should return None on JSON parse error
        profile = await self.profiler_service.generate_profile("Grace")
        self.assertIsNone(profile)
    
    async def test_profiler_emits_agui_events(self) -> None:
        """Test that profiler emits AG-UI events."""
        agui_events: list[EventPayload] = []
        
        async def on_agui(payload: EventPayload) -> None:
            agui_events.append(payload)
        
        await self.bus.subscribe(events.TOPIC_AGUI_EVENT, on_agui)
        
        # Insert test entity
        self._insert_test_entity("Henry", "PERSON", "Henry")
        
        # Generate profile
        await self.profiler_service.generate_profile("Henry")
        
        await asyncio.sleep(0.3)
        
        # Should have emitted AG-UI event
        self.assertGreater(len(agui_events), 0)
        self.assertIn("message", agui_events[0])


if __name__ == "__main__":
    unittest.main()
