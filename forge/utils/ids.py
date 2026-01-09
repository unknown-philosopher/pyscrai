"""
ID generation utilities for Forge 3.0.

Thread-safe unique identifier generation for entities and events.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forge.core.models.entity import EntityType


# ============================================================================
# Thread-Safe Counter
# ============================================================================


class _ThreadSafeCounter:
    """Thread-safe incrementing counter."""
    
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def next(self) -> int:
        """Get the next counter value."""
        with self._lock:
            self._value += 1
            return self._value
    
    def reset(self) -> None:
        """Reset counter to zero."""
        with self._lock:
            self._value = 0


# Global counter instance
_counter = _ThreadSafeCounter()


# ============================================================================
# ID Generation Functions
# ============================================================================


def generate_id(prefix: str = "") -> str:
    """Generate a unique identifier.
    
    Format: {prefix}_{timestamp}_{counter}
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique string identifier
        
    Example:
        >>> generate_id("ACT")
        "ACT_1704067200_001"
    """
    timestamp = int(time.time())
    count = _counter.next()
    
    if prefix:
        return f"{prefix}_{timestamp}_{count:03d}"
    else:
        return f"{timestamp}_{count:03d}"


def generate_entity_id(entity_type: "EntityType") -> str:
    """Generate an ID for a specific entity type.
    
    Args:
        entity_type: Type of entity
        
    Returns:
        Type-prefixed unique ID
        
    Example:
        >>> generate_entity_id(EntityType.ACTOR)
        "ACT_1704067200_001"
    """
    # Import here to avoid circular import
    from forge.core.models.entity import EntityType
    
    prefixes = {
        EntityType.ACTOR: "ACT",
        EntityType.POLITY: "POL",
        EntityType.LOCATION: "LOC",
        EntityType.REGION: "REG",
        EntityType.RESOURCE: "RES",
        EntityType.EVENT: "EVT",
        EntityType.ABSTRACT: "ABS",
    }
    
    prefix = prefixes.get(entity_type, "ENT")
    return generate_id(prefix)


def generate_relationship_id() -> str:
    """Generate an ID for a relationship."""
    return generate_id("REL")


def generate_event_id() -> str:
    """Generate an ID for an event."""
    return generate_id("EV")


def generate_session_id() -> str:
    """Generate a session identifier."""
    return generate_id("SESS")


# ============================================================================
# ID Parsing
# ============================================================================


def parse_id(entity_id: str) -> tuple[str, int, int]:
    """Parse an ID into its components.
    
    Args:
        entity_id: The ID to parse
        
    Returns:
        Tuple of (prefix, timestamp, counter)
        
    Raises:
        ValueError: If ID format is invalid
    """
    parts = entity_id.rsplit("_", 2)
    
    if len(parts) == 3:
        prefix, ts_str, count_str = parts
        return prefix, int(ts_str), int(count_str)
    elif len(parts) == 2:
        ts_str, count_str = parts
        return "", int(ts_str), int(count_str)
    else:
        raise ValueError(f"Invalid ID format: {entity_id}")


def get_id_prefix(entity_id: str) -> str:
    """Extract the prefix from an ID."""
    parts = entity_id.split("_")
    if len(parts) >= 3:
        return parts[0]
    return ""


def get_id_timestamp(entity_id: str) -> int:
    """Extract the timestamp from an ID."""
    prefix, timestamp, _ = parse_id(entity_id)
    return timestamp


# ============================================================================
# Validation
# ============================================================================


def is_valid_id(entity_id: str) -> bool:
    """Check if a string is a valid Forge ID."""
    try:
        parse_id(entity_id)
        return True
    except (ValueError, TypeError):
        return False


def is_entity_type_id(entity_id: str, entity_type: "EntityType") -> bool:
    """Check if an ID belongs to a specific entity type.
    
    Args:
        entity_id: The ID to check
        entity_type: Expected entity type
        
    Returns:
        True if ID matches the entity type prefix
    """
    from forge.core.models.entity import EntityType
    
    prefixes = {
        EntityType.ACTOR: "ACT",
        EntityType.POLITY: "POL",
        EntityType.LOCATION: "LOC",
        EntityType.REGION: "REG",
        EntityType.RESOURCE: "RES",
        EntityType.EVENT: "EVT",
        EntityType.ABSTRACT: "ABS",
    }
    
    expected_prefix = prefixes.get(entity_type, "ENT")
    return get_id_prefix(entity_id) == expected_prefix


# ============================================================================
# Test/Reset Functions
# ============================================================================


def reset_counter() -> None:
    """Reset the ID counter (for testing only)."""
    _counter.reset()
