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
    from forge.phases.p0_extraction.chunker import TextChunker
    from forge.phases.p0_extraction.extractor import EntityExtractor
    from forge.phases.p0_extraction.sentinel import Sentinel
    from forge.phases.p0_extraction.orchestrator import ExtractionOrchestrator
    print("  ✓ Extraction phase")
    
    from forge.phases.p5_finalize.manager import EntityManager
    from forge.phases.p5_finalize.merger import EntityMerger
    from forge.phases.p5_finalize.orchestrator import FinalizeOrchestrator
    print("  ✓ Finalize phase (Anvil)")
    
    from forge.phases.p2_relationships.graph import GraphManager
    from forge.phases.p2_relationships.analysis import GraphAnalyzer
    from forge.phases.p2_relationships.orchestrator import RelationshipsOrchestrator
    print("  ✓ Relationships phase (Loom)")
    
    # Agents
    from forge.agents.base import Agent, AgentRole
    from forge.agents.analyst import AnalystAgent
    from forge.agents.reviewer import ReviewerAgent
    from forge.agents.validator import ValidatorAgent
    print("  ✓ Agents system")
    
    # Advisors
    from forge.agents.advisors import (
        OSINTAdvisor, HUMINTAdvisor, SIGINTAdvisor,
        SYNTHAdvisor, GEOINTAdvisor, ANVILAdvisor
    )
    print("  ✓ Advisors (OSINT, HUMINT, SIGINT, SYNTH, GEOINT, ANVIL)")
    
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


def test_text_chunker():
    """Test text chunking for extraction."""
    print("\nTesting text chunker...")
    
    from forge.phases.p0_extraction.chunker import TextChunker
    
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


def test_prompt_manager():
    """Test the prompt manager with externalized YAML prompts."""
    print("\nTesting prompt manager...")
    
    from forge.agents.prompts import get_prompt_manager, PromptManager
    
    manager = get_prompt_manager()
    
    # List prompts - should include YAML-loaded prompts
    prompts = manager.list_prompts()
    
    # Check extraction prompts loaded from extraction.yaml
    assert "extraction.system_prompt" in prompts
    assert "extraction.user_prompt_template" in prompts
    print(f"  ✓ Extraction prompts loaded")
    
    # Check analysis prompts loaded from analysis.yaml
    assert "analysis.system_prompt" in prompts
    assert "analysis.analyze_entity_prompt" in prompts
    print(f"  ✓ Analysis prompts loaded")
    
    # Check review prompts loaded from review.yaml
    assert "review.system_prompt" in prompts
    assert "review.review_entity_prompt" in prompts
    print(f"  ✓ Review prompts loaded")
    
    # Check advisor prompts loaded from advisors/*.yaml
    assert "osint.system_prompt" in prompts
    assert "humint.system_prompt" in prompts
    assert "sigint.system_prompt" in prompts
    assert "synth.system_prompt" in prompts
    assert "geoint.system_prompt" in prompts
    assert "anvil.system_prompt" in prompts
    print(f"  ✓ Advisor prompts loaded (6 advisors)")
    
    # Test Jinja2 rendering
    rendered = manager.render(
        "extraction.user_prompt_template",
        source_name="test.txt",
        chunk_info="CHUNK: 1",
        text_content="John Smith met with the CIA director.",
        context="Intelligence report"
    )
    assert "John Smith" in rendered
    assert "CIA director" in rendered
    print("  ✓ Jinja2 template rendering works")
    
    print(f"  ✓ Total prompts loaded: {len(prompts)}")
    
    print("\n✅ Prompt manager tests passed!")


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


def test_advisor_system():
    """Test the phase-specific advisor system."""
    print("\nTesting advisor system...")
    
    from forge.agents.advisors import (
        OSINTAdvisor, HUMINTAdvisor, SIGINTAdvisor,
        SYNTHAdvisor, GEOINTAdvisor, ANVILAdvisor
    )
    from forge.agents.prompts import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # Test each advisor has its system prompt
    advisors = [
        ("OSINT", "osint.system_prompt", "p0_extraction"),
        ("HUMINT", "humint.system_prompt", "p1_entities"),
        ("SIGINT", "sigint.system_prompt", "p2_relationships"),
        ("SYNTH", "synth.system_prompt", "p3_narrative"),
        ("GEOINT", "geoint.system_prompt", "p4_map"),
        ("ANVIL", "anvil.system_prompt", "p5_finalize"),
    ]
    
    for name, prompt_key, phase in advisors:
        prompt = manager.get(prompt_key)
        assert prompt is not None, f"{name} system prompt not found"
        assert len(prompt) > 100, f"{name} prompt too short"
        print(f"  ✓ {name} advisor prompt loaded ({phase})")
    
    # Verify advisor classes can be instantiated (type check)
    assert OSINTAdvisor is not None
    assert HUMINTAdvisor is not None
    assert SIGINTAdvisor is not None
    assert SYNTHAdvisor is not None
    assert GEOINTAdvisor is not None
    assert ANVILAdvisor is not None
    print("  ✓ All advisor classes available")
    
    print("\n✅ Advisor system tests passed!")


def test_llm_models():
    """Test LLM message and conversation models."""
    print("\nTesting LLM models...")
    
    from forge.systems.llm.models import LLMMessage, MessageRole, Conversation
    
    # Test message creation
    msg = LLMMessage(
        role=MessageRole.USER,
        content="Hello, world!",
        tokens_used=5
    )
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello, world!"
    print("  ✓ LLMMessage creation")
    
    # Test API format conversion
    api_format = msg.to_api_format()
    assert api_format["role"] == "user"
    assert api_format["content"] == "Hello, world!"
    print("  ✓ Message to API format")
    
    # Test dict serialization
    msg_dict = msg.to_dict()
    restored = LLMMessage.from_dict(msg_dict)
    assert restored.role == msg.role
    assert restored.content == msg.content
    print("  ✓ Message serialization/deserialization")
    
    # Test conversation
    conv = Conversation(
        id="conv_001",
        title="Test Conversation",
        system_prompt="You are a helpful assistant.",
    )
    conv.add_message(msg)
    conv.add_message(LLMMessage(role=MessageRole.ASSISTANT, content="Hi there!"))
    
    assert len(conv.messages) == 2
    assert conv.total_tokens == 5
    print(f"  ✓ Conversation with {len(conv.messages)} messages")
    
    # Test API messages with system prompt
    api_messages = conv.get_messages_for_api()
    assert api_messages[0]["role"] == "system"
    assert len(api_messages) == 3
    print("  ✓ Conversation to API format (with system prompt)")
    
    print("\n✅ LLM models tests passed!")


def test_file_manager():
    """Test file I/O operations."""
    print("\nTesting file manager...")
    
    from forge.systems.storage.file_io import FileManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        fm = FileManager(tmpdir)
        fm.ensure_directories()
        
        # Check directories created
        assert fm.staging_path.exists()
        assert fm.sources_path.exists()
        assert fm.logs_path.exists()
        print("  ✓ Directory structure created")
        
        # Write staging JSON
        test_data = {"entities": [{"name": "John", "type": "actor"}]}
        path = fm.write_staging_json("test_entities.json", test_data)
        assert path.exists()
        print(f"  ✓ Written staging JSON: {path.name}")
        
        # Read staging JSON
        loaded = fm.read_staging_json("test_entities.json")
        assert loaded["entities"][0]["name"] == "John"