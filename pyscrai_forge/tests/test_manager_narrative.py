import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

from pyscrai_forge.agents.manager import ForgeManager
from pyscrai_forge.prompts.narrative import NarrativeMode


class MockProvider:
    def __init__(self):
        self.default_model = "test-model"
        
    async def complete_simple(self, prompt: str, model: str, system_prompt: str | None = None, temperature: float = 0.7):
        # Simple mock that returns a test narrative
        if "verify" in prompt.lower():
            return "PASS"
        return "This is a test narrative about the entities."


class MockController:
    def __init__(self):
        from pyscrai_core import ProjectManifest
        self.manifest = ProjectManifest(name="Test Project", description="Test")
        self.database_path = Path("/fake/path")


class MockEntity:
    def __init__(self, name, entity_type="actor", resources=None):
        from pyscrai_core import DescriptorComponent, StateComponent, EntityType
        self.id = f"ent_{name.lower()}_001"
        self.descriptor = DescriptorComponent(
            name=name,
            entity_type=EntityType.ACTOR if entity_type == "actor" else EntityType.POLITY,
            bio=f"Test {entity_type}"
        )
        self.state = StateComponent(
            resources_json=json.dumps(resources or {})
        )


@pytest.mark.asyncio
async def test_generate_project_narrative():
    provider = MockProvider()
    manager = ForgeManager(provider)
    manager.controller = MockController()
    
    # Mock storage.load_all_entities to return test entities
    import pyscrai_forge.src.storage as storage
    original_load = storage.load_all_entities
    
    def mock_load_entities(db_path):
        return [
            MockEntity("Captain Alpha", "actor", {"health": 100, "rank": "Captain"}),
            MockEntity("Beta Corp", "polity", {"wealth": 50000})
        ]
    
    storage.load_all_entities = mock_load_entities
    
    try:
        # Test auto-mode detection
        result = await manager.generate_project_narrative()
        assert "test narrative" in result.lower()
        
        # Test explicit mode
        result = await manager.generate_project_narrative(mode="sitrep", focus="Military Status")
        assert "test narrative" in result.lower()
        
    finally:
        storage.load_all_entities = original_load


@pytest.mark.asyncio 
async def test_tool_generate_narrative():
    provider = MockProvider()
    manager = ForgeManager(provider)
    manager.controller = MockController()
    
    # Mock storage.load_all_entities
    import pyscrai_forge.src.storage as storage
    original_load = storage.load_all_entities
    storage.load_all_entities = lambda db_path: [MockEntity("Test Entity")]
    
    try:
        tool_call = {
            "tool": "generate_narrative",
            "params": {"mode": "summary", "focus": "Test Focus"}
        }
        
        result = await manager._execute_tool(tool_call)
        assert "NARRATIVE_GENERATED" in result
        assert "test narrative" in result.lower()
        
    finally:
        storage.load_all_entities = original_load