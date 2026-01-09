"""
Forge 3.0 Test Suite

Run this script to verify the new Forge system is working correctly.

Usage:
    python -m forge.tests.test_forge
    
Or run individual tests:
    python -m pytest forge/tests/test_forge.py -v
"""

import asyncio
import tempfile
import shutil
from pathlib import Path

# Test imports - if these fail, there's an import problem
def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")
    
    # Core models
    from forge.core.models.entity import Entity, EntityType, create_actor, create_location
    from forge.core.models.relationship import Relationship, RelationType
    from forge.core.models.project import ProjectManifest, ProjectManager
    print("  ✓ Core models")
    
    # Events
    from forge.core.events.base import BaseEvent, EventType
    from forge.core.events.mutations import StateChangeEvent
    print("  ✓ Events system")
    
    # Systems
    from forge.systems.llm.models import LLMMessage, LLMResponse
    from forge.systems.llm.base import LLMProvider
    from forge.systems.llm.provider_factory import ProviderFactory, ProviderType
    print("  ✓ LLM interface")
    
    from forge.systems.memory.embeddings import EmbeddingModel
    from forge.systems.memory.vector_memory import VectorMemory
    print("  ✓ Memory system")
    
    from forge.systems.storage.database import DatabaseManager
    from forge.systems.storage.file_io import FileManager
    print("  ✓ Storage system")
    
    # Phases
    from forge.phases.extraction.chunker import TextChunker
    from forge.phases.extraction.extractor import EntityExtractor
    from forge.phases.extraction.sentinel import Sentinel
    from forge.phases.extraction.orchestrator import ExtractionOrchestrator
    print("  ✓ Extraction phase")
    
    from forge.phases.anvil.manager import EntityManager
    from forge.phases.anvil.merger import EntityMerger
    from forge.phases.anvil.orchestrator import AnvilOrchestrator
    print("  ✓ Anvil phase")
    
    from forge.phases.loom.graph import GraphManager
    from forge.phases.loom.analysis import GraphAnalyzer
    from forge.phases.loom.orchestrator import LoomOrchestrator
    print("  ✓ Loom phase")
    
    # Agents
    from forge.agents.base import Agent, AgentRole
    from forge.agents.analyst import AnalystAgent
    from forge.agents.reviewer import ReviewerAgent
    from forge.agents.validator import ValidatorAgent
    print("  ✓ Agents system")
    
    # Advisors
    from forge.agents.advisors import EntityAdvisor, RelationshipAdvisor
    print("  ✓ Advisors")
    
    # Prompts
    from forge.agents.prompts import PromptManager
    print("  ✓ Prompt manager")
    
    # Prefabs
    from forge.prefabs import PrefabSchema, PrefabLoader, PrefabRegistry
    print("  ✓ Prefabs system")
    
    # Utils
    from forge.utils.logging import get_logger, setup_logging
    from forge.utils.ids import generate_entity_id, generate_relationship_id
    print("  ✓ Utils")
    
    # App
    from forge.app.config import ForgeConfig, get_config
    from forge.app.state import ForgeState
    print("  ✓ App layer")
    
    print("\n✅ All imports successful!")
    return True


def test_entity_creation():
    """Test entity creation and manipulation."""
    print("\nTesting entity creation...")
    
    from forge.core.models.entity import (
        Entity, EntityType, create_actor, create_location, create_polity
    )
    
    # Create entities using helper functions
    actor = create_actor(
        name="John Smith",
        description="A mysterious intelligence operative",
        aliases=["The Shadow", "Agent X"],
        attributes={"codename": "Nightfall", "clearance": "TOP_SECRET"}
    )
    
    assert actor.entity_type == EntityType.ACTOR
    assert actor.name == "John Smith"
    assert "The Shadow" in actor.aliases
    assert actor.attributes["codename"] == "Nightfall"
    print(f"  ✓ Created actor: {actor.name} (ID: {actor.id})")
    
    location = create_location(
        name="Safe House Alpha",
        description="A secure facility in Berlin",
        attributes={"city": "Berlin", "security_level": "HIGH"}
    )
    
    assert location.entity_type == EntityType.LOCATION
    print(f"  ✓ Created location: {location.name}")
    
    polity = create_polity(
        name="Central Intelligence Agency",
        description="US foreign intelligence service",
        aliases=["CIA", "The Company", "Langley"]
    )
    
    assert polity.entity_type == EntityType.POLITY
    assert "CIA" in polity.aliases
    print(f"  ✓ Created polity: {polity.name}")
    
    print("\n✅ Entity creation tests passed!")
    return True


def test_relationship_creation():
    """Test relationship creation."""
    print("\nTesting relationship creation...")
    
    from forge.core.models.entity import create_actor, create_polity
    from forge.core.models.relationship import Relationship, RelationType
    
    agent = create_actor("James Bond", "MI6 operative")
    mi6 = create_polity("MI6", "British Secret Intelligence Service")
    
    rel = Relationship(
        source_id=agent.id,
        target_id=mi6.id,
        relationship_type=RelationType.MEMBER_OF,
        strength=0.9,
        description="Bond is a 00 agent for MI6"
    )
    
    assert rel.source_id == agent.id
    assert rel.target_id == mi6.id
    assert rel.relationship_type == RelationType.MEMBER_OF
    print(f"  ✓ Created relationship: {agent.name} --[{rel.relationship_type.value}]--> {mi6.name}")
    
    print("\n✅ Relationship creation tests passed!")
    return True


def test_database_operations():
    """Test database CRUD operations."""
    print("\nTesting database operations...")
    
    from forge.core.models.entity import create_actor
    from forge.systems.storage.database import DatabaseManager
    
    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DatabaseManager(str(db_path))
        db.initialize()
        print(f"  ✓ Created database at {db_path}")
        
        # Save entity
        actor = create_actor("Test Actor", "A test entity")
        db.save_entity(actor)
        print(f"  ✓ Saved entity: {actor.name}")
        
        # Retrieve entity
        retrieved = db.get_entity(actor.id)
        assert retrieved is not None
        assert retrieved.name == actor.name
        print(f"  ✓ Retrieved entity: {retrieved.name}")
        
        # Get all entities
        all_entities = db.get_all_entities()
        assert len(all_entities) == 1
        print(f"  ✓ Get all entities: {len(all_entities)} found")
        
        # Delete entity
        db.delete_entity(actor.id)
        deleted = db.get_entity(actor.id)
        assert deleted is None
        print("  ✓ Deleted entity")
    
    print("\n✅ Database operation tests passed!")
    return True


def test_id_generation():
    """Test ID generation utilities."""
    print("\nTesting ID generation...")
    
    from forge.utils.ids import (
        generate_id,
        generate_relationship_id,
        generate_event_id,
        parse_id,
        is_valid_id,
        get_id_prefix
    )
    
    # Generate IDs
    ent_id = generate_id("ACT")
    rel_id = generate_relationship_id()
    evt_id = generate_event_id()
    
    assert ent_id.startswith("ACT_")
    assert rel_id.startswith("REL_")
    assert evt_id.startswith("EV_")
    print(f"  ✓ Generated entity ID: {ent_id}")
    print(f"  ✓ Generated relationship ID: {rel_id}")
    print(f"  ✓ Generated event ID: {evt_id}")
    
    # Parse ID
    prefix, timestamp, counter = parse_id(ent_id)
    assert prefix == "ACT"
    assert timestamp > 0
    assert counter >= 1
    print(f"  ✓ Parsed ID: prefix={prefix}, timestamp={timestamp}, counter={counter}")
    
    # Get prefix
    assert get_id_prefix(ent_id) == "ACT"
    print("  ✓ Get ID prefix works")
    
    # Validate
    assert is_valid_id(ent_id)
    assert not is_valid_id("invalid")
    print("  ✓ ID validation works")
    
    print("\n✅ ID generation tests passed!")
    return True


def test_text_chunker():
    """Test text chunking for extraction."""
    print("\nTesting text chunker...")
    
    from forge.phases.extraction.chunker import TextChunker
    
    chunker = TextChunker(chunk_size=100, overlap=20)
    
    text = """This is a test document with multiple paragraphs.

    The second paragraph contains important information about entities.
    
    The third paragraph discusses relationships between these entities.
    We need to make sure the chunker handles this correctly.
    
    Final paragraph with concluding remarks."""
    
    chunks = list(chunker.chunk_text(text, source_name="test.txt"))
    
    assert len(chunks) >= 1
    print(f"  ✓ Created {len(chunks)} chunks from text")
    
    for i, chunk in enumerate(chunks):
        print(f"    Chunk {i+1}: {chunk.char_count} chars, {chunk.word_count} words")
    
    print("\n✅ Text chunker tests passed!")
    return True


def test_prefab_system():
    """Test the prefab schema system."""
    print("\nTesting prefab system...")
    
    from forge.prefabs import PrefabSchema, PrefabRegistry, FieldType
    from forge.prefabs.schema import get_default_actor_schema
    
    # Test default schema
    actor_schema = get_default_actor_schema()
    assert actor_schema.name == "actor_default"
    assert actor_schema.entity_type == "ACTOR"
    print(f"  ✓ Default actor schema: {len(actor_schema.fields)} fields")
    
    # Test registry
    registry = PrefabRegistry()
    registry.load_defaults()
    
    schemas = registry.list_schemas()
    assert "actor_default" in schemas
    assert "location_default" in schemas
    assert "polity_default" in schemas
    print(f"  ✓ Registry loaded {len(schemas)} default schemas")
    
    # Test validation
    valid_attrs = {"status": "active"}
    errors = actor_schema.validate(valid_attrs)
    assert len(errors) == 0
    print("  ✓ Schema validation works")
    
    print("\n✅ Prefab system tests passed!")
    return True


def test_prompt_manager():
    """Test the prompt manager."""
    print("\nTesting prompt manager...")
    
    from forge.agents.prompts.manager import PromptManager, create_default_manager
    
    manager = create_default_manager()
    
    # List prompts
    prompts = manager.list_prompts()
    assert "extraction_system" in prompts
    assert "extraction_user" in prompts
    print(f"  ✓ Default prompts: {prompts}")
    
    # Render prompt
    rendered = manager.render(
        "extraction_user",
        document="This is a test document about John Smith, a CIA operative."
    )
    assert "John Smith" in rendered
    print("  ✓ Prompt rendering works")
    
    print("\n✅ Prompt manager tests passed!")
    return True


def test_event_system():
    """Test the event system."""
    print("\nTesting event system...")
    
    from forge.core.events.base import BaseEvent, EventType
    from forge.core.events.mutations import StateChangeEvent
    from forge.core.models.entity import create_actor
    
    actor = create_actor("Event Test", "Testing events")
    
    # Create event using factory function
    from forge.core.events.mutations import create_entity_created_event
    event = create_entity_created_event(
        entity_id=actor.id,
        entity_type=actor.entity_type.value,
        name=actor.name,
    )
    
    assert event.event_type == EventType.ENTITY_CREATED
    assert event.target_id == actor.id
    print(f"  ✓ Created event: {event.event_type.value}")
    
    # State change event
    state_event = StateChangeEvent(
        target_id=actor.id,
        field_name="status",
        old_value="unknown",
        new_value="active",
    )
    assert state_event.event_type == EventType.STATE_CHANGE
    print(f"  ✓ State change event: {state_event.field_name}")
    
    print("\n✅ Event system tests passed!")
    return True


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("FORGE 3.0 TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_entity_creation,
        test_relationship_creation,
        test_database_operations,
        test_id_generation,
        test_text_chunker,
        test_prefab_system,
        test_prompt_manager,
        test_event_system,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
