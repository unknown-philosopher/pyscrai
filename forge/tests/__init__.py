"""
Forge 3.0 Test Suite

Modular test organization for easier maintenance and expansion.

Test Modules:
- test_imports.py: Import verification for all core modules
- test_core.py: Entity, relationship, and event models  
- test_utils.py: ID generation and utility functions
- test_systems.py: Database, file I/O, LLM models, vector memory
- test_phases.py: Text chunking, sentinel, graph analysis
- test_agents.py: Prompt manager and advisor system
- test_prefabs.py: Schema prefab system and registry
- test_app.py: Config, project manifest, and state management

Run all tests:
    pytest forge/tests/ -v

Run specific module:
    pytest forge/tests/test_core.py -v
    
Run individual test:
    pytest forge/tests/test_core.py::test_entity_creation -v
"""

__all__ = [
    # Import tests
    "test_imports",
    
    # Core model tests
    "test_entity_creation",
    "test_relationship_creation", 
    "test_event_system",
    
    # Utility tests
    "test_id_generation",
    
    # System tests
    "test_database_operations",
    "test_file_manager",
    "test_llm_models",
    "test_vector_memory_serialization",
    
    # Phase tests
    "test_text_chunker",
    "test_sentinel_merge_candidate",
    "test_graph_manager",
    
    # Agent tests
    "test_prompt_manager",
    "test_advisor_system",
    
    # Prefab tests
    "test_prefab_system",
    
    # App tests
    "test_forge_config",
    "test_project_manifest",
    "test_forge_state_creation",
]
