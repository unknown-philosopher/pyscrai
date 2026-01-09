"""
Test Suite: Prefabs

Tests for schema prefab system and registry.
"""

from pathlib import Path


def test_prefab_system():
    """Test the prefab schema system."""
    print("\nTesting prefab system...")
    
    from forge.prefabs import PrefabSchema, PrefabRegistry, FieldType
    from forge.prefabs.loader import PrefabLoader
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
    
    # Test schema field types
    for field in actor_schema.fields:
        assert hasattr(field, "name")
        assert hasattr(field, "type")
        assert isinstance(field.type, FieldType)
    print(f"  ✓ All schema fields have proper structure")
    
    # Test loading custom JSON prefabs
    loader = PrefabLoader(registry)
    schemas_dir = Path(__file__).parent.parent / "prefabs" / "schemas"
    loader.load_directory(schemas_dir)
    
    espionage_actor = registry.get("actor_espionage")
    if espionage_actor:
        assert espionage_actor.entity_type.upper() == "ACTOR"
        print(f"  ✓ Loaded custom schema: {espionage_actor.name}")
    
    safehouse_location = registry.get("location_safehouse")
    if safehouse_location:
        assert safehouse_location.entity_type.upper() == "LOCATION"
        print(f"  ✓ Loaded custom schema: {safehouse_location.name}")
    
    agency_polity = registry.get("polity_agency")
    if agency_polity:
        assert agency_polity.entity_type.upper() == "POLITY"
        print(f"  ✓ Loaded custom schema: {agency_polity.name}")
    
    print("\n✅ Prefab system tests passed!")
