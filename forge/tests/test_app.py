"""
Test Suite: Application Layer

Tests for ForgeConfig, ProjectManifest, and ForgeState.
"""
import tempfile
from pathlib import Path


def test_forge_config():
    """Test LLMConfig, ExtractionConfig, UIConfig."""
    print("\nTesting Forge configuration...")
    
    from forge.app.config import (
        ForgeConfig, LLMConfig, ExtractionConfig, UIConfig, 
        get_config, set_config
    )
    
    # Test default config creation
    config = ForgeConfig()
    assert config.llm is not None
    assert config.extraction is not None
    assert config.ui is not None
    print("  ✓ Created default ForgeConfig")
    
    # Test LLM config
    llm_config = LLMConfig(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test_key",
        temperature=0.7,
        max_tokens=4000
    )
    assert llm_config.provider == "openrouter"
    assert llm_config.model == "anthropic/claude-3.5-sonnet"
    assert llm_config.temperature == 0.7
    print(f"  ✓ LLMConfig: {llm_config.provider}/{llm_config.model}")
    
    # Test Extraction config
    extract_config = ExtractionConfig(
        chunk_size=1000,
        chunk_overlap=200,
        similarity_threshold=0.85,
        auto_merge_threshold=0.95,
        max_entities_per_chunk=15
    )
    assert extract_config.chunk_size == 1000
    assert extract_config.chunk_overlap == 200
    assert extract_config.similarity_threshold == 0.85
    print(f"  ✓ ExtractionConfig: chunk_size={extract_config.chunk_size}")
    
    # Test UI config
    ui_config = UIConfig(
        theme="dark",
        window_width=1400,
        window_height=900,
        font_family="Segoe UI",
        font_size=10
    )
    assert ui_config.theme == "dark"
    assert ui_config.window_width == 1400
    print(f"  ✓ UIConfig: theme={ui_config.theme}")
    
    # Test config with custom values
    custom_config = ForgeConfig(
        llm=llm_config,
        extraction=extract_config,
        ui=ui_config
    )
    assert custom_config.llm.provider == "openrouter"
    assert custom_config.extraction.chunk_size == 1000
    assert custom_config.ui.theme == "dark"
    print("  ✓ Custom ForgeConfig with all subsystems")
    
    # Test global config management
    set_config(custom_config)
    retrieved = get_config()
    assert retrieved.llm.provider == "openrouter"
    print("  ✓ Global config get/set works")
    
    # Test serialization
    config_dict = custom_config.to_dict()
    assert "llm" in config_dict
    assert "extraction" in config_dict
    assert "ui" in config_dict
    print("  ✓ Config serialization works")
    
    # Test deserialization
    restored = ForgeConfig.from_dict(config_dict)
    assert restored.llm.provider == custom_config.llm.provider
    assert restored.extraction.chunk_size == custom_config.extraction.chunk_size
    print("  ✓ Config deserialization works")
    
    print("\n✅ Forge configuration tests passed!")


def test_project_manifest():
    """Test ProjectManifest Pydantic model."""
    print("\nTesting ProjectManifest...")
    
    from forge.core.models.project import ProjectManifest
    from datetime import datetime, UTC
    
    # Create manifest with basic info
    manifest = ProjectManifest(
        name="Test Project",
        description="A test intelligence project",
        author="Test User",
        version="1.0.0",
        llm_provider="openrouter",
        llm_default_model="openai/gpt-4.1-mini"
    )
    
    assert manifest.version == "1.0.0"
    assert manifest.name == "Test Project"
    assert manifest.author == "Test User"
    print(f"  ✓ Created manifest: {manifest.name}")
    
    # Test timestamps
    assert isinstance(manifest.created_at, datetime)
    assert isinstance(manifest.last_modified_at, datetime)
    print("  ✓ Timestamps auto-generated")
    
    # Test entity schemas
    assert "actor" in manifest.entity_schemas
    assert "polity" in manifest.entity_schemas
    assert "location" in manifest.entity_schemas
    print("  ✓ Default entity schemas created")
    
    # Test JSON serialization
    manifest_json = manifest.model_dump_json()
    assert "Test Project" in manifest_json
    print("  ✓ Manifest serializes to JSON")
    
    # Test deserialization
    restored = ProjectManifest.model_validate_json(manifest_json)
    assert restored.name == manifest.name
    assert restored.version == manifest.version
    assert restored.author == manifest.author
    print("  ✓ Manifest deserializes from JSON")
    
    # Test manifest saving/loading
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "project.json"
        
        # Save
        with open(manifest_path, "w") as f:
            f.write(manifest.model_dump_json(indent=2))
        
        assert manifest_path.exists()
        print(f"  ✓ Saved manifest to {manifest_path.name}")
        
        # Load
        with open(manifest_path, "r") as f:
            loaded = ProjectManifest.model_validate_json(f.read())
        
        assert loaded.name == manifest.name
        assert loaded.version == manifest.version
        print("  ✓ Loaded manifest from file")
    
    print("\n✅ ProjectManifest tests passed!")


def test_forge_state_creation():
    """Test ForgeState lazy initialization."""
    print("\nTesting ForgeState creation...")
    
    from forge.app.state import ForgeState
    from forge.app.config import ForgeConfig
    
    # Create config
    config = ForgeConfig()
    
    # Initialize ForgeState using factory method
    state = ForgeState.create(config)
    
    assert state.config is not None
    assert state.session_id != ""
    assert state.project is None  # No project loaded yet
    print(f"  ✓ Created ForgeState with session: {state.session_id}")
    
    # Test lazy initialization - systems should not be initialized yet
    assert state._db is None
    assert state._llm_provider is None
    assert state._vector_memory is None
    print("  ✓ Systems not initialized until needed (lazy init)")
    
    # Test state immutability checks
    assert state.dirty is False
    print("  ✓ State initialized as clean (not dirty)")
    
    # Test multiple state instances can be created
    state2 = ForgeState.create(config)
    assert state2.session_id != state.session_id
    print("  ✓ Multiple state instances have unique session IDs")
    
    print("\n✅ ForgeState creation tests passed!")
