"""
Test Suite: Import Checks

Verifies all core modules can be imported successfully.
"""


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
