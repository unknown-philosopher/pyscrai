"""
Test Suite: Core Models

Tests for Entity, Relationship, and Event models.
"""


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
