"""
Test Suite: Utilities

Tests for ID generation, logging, and other utility functions.
"""


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
