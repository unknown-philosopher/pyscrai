"""Simple database storage layer for Harvester entities.

This module provides a lightweight interface for storing and retrieving
entities and relationships in world.db. Used by the forge to commit
extracted data.

Decoupled from UI: The forge calls these functions, not raw SQL.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship


def init_harvester_tables(db_path: Path) -> None:
    """Initialize entities and relationships tables in world.db.
    
    Creates tables if they don't exist. Safe to call multiple times.
    
    Args:
        db_path: Path to world.db file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Entities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Relationships table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            strength REAL NOT NULL,
            description TEXT,
            data_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES entities(id),
            FOREIGN KEY (target_id) REFERENCES entities(id)
        )
    """)
    
    # Indexes for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_type 
        ON entities(entity_type)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_relationships_source 
        ON relationships(source_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_relationships_target 
        ON relationships(target_id)
    """)
    
    conn.commit()
    conn.close()


def save_entity(db_path: Path, entity: Entity) -> None:
    """Save an entity to the database.
    
    If entity with same ID exists, it will be updated.
    
    Args:
        db_path: Path to world.db
        entity: Entity to save
    """
    from datetime import UTC, datetime
    
    init_harvester_tables(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    now = datetime.now(UTC).isoformat()
    data_json = entity.model_dump_json()
    entity_type = entity.descriptor.entity_type.value if entity.descriptor else "UNKNOWN"
    
    cursor.execute("""
        INSERT OR REPLACE INTO entities (id, entity_type, data_json, created_at, updated_at)
        VALUES (?, ?, ?, 
            COALESCE((SELECT created_at FROM entities WHERE id = ?), ?),
            ?)
    """, (entity.id, entity_type, data_json, entity.id, now, now))
    
    conn.commit()
    conn.close()


def save_relationship(db_path: Path, relationship: Relationship) -> None:
    """Save a relationship to the database.
    
    If relationship with same ID exists, it will be updated.
    
    Args:
        db_path: Path to world.db
        relationship: Relationship to save
    """
    from datetime import UTC, datetime
    
    init_harvester_tables(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    now = datetime.now(UTC).isoformat()
    # Store relationship metadata
    data_json = json.dumps({
        "visibility": relationship.visibility.value if hasattr(relationship, "visibility") else "PUBLIC",
        "metadata": relationship.metadata if hasattr(relationship, "metadata") else "{}",
    })
    
    cursor.execute("""
        INSERT OR REPLACE INTO relationships 
        (id, source_id, target_id, relationship_type, strength, description, data_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?,
            COALESCE((SELECT created_at FROM relationships WHERE id = ?), ?),
            ?)
    """, (
        relationship.id,
        relationship.source_id,
        relationship.target_id,
        relationship.relationship_type.value,
        relationship.strength,
        relationship.description,
        data_json,
        relationship.id,
        now,
        now,
    ))
    
    conn.commit()
    conn.close()


def load_entity(db_path: Path, entity_id: str) -> Entity | None:
    """Load an entity from the database.
    
    Args:
        db_path: Path to world.db
        entity_id: Entity ID to load
        
    Returns:
        Entity if found, None otherwise
    """
    from pyscrai_core import Actor, Entity, EntityType, Location, Polity
    
    init_harvester_tables(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT data_json FROM entities WHERE id = ?", (entity_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    data = json.loads(row[0])
    
    # Determine entity class from type
    entity_type_str = data.get("descriptor", {}).get("entity_type", "ABSTRACT")
    try:
        entity_type = EntityType(entity_type_str)
    except ValueError:
        entity_type = EntityType.ABSTRACT
    
    if entity_type == EntityType.ACTOR:
        return Actor.model_validate(data)
    elif entity_type == EntityType.POLITY:
        return Polity.model_validate(data)
    elif entity_type == EntityType.LOCATION:
        return Location.model_validate(data)
    else:
        return Entity.model_validate(data)


def load_all_entities(db_path: Path) -> list[Entity]:
    """Load all entities from the database.
    
    Args:
        db_path: Path to world.db
        
    Returns:
        List of all entities
    """
    from pyscrai_core import Actor, Entity, EntityType, Location, Polity
    
    init_harvester_tables(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT data_json FROM entities ORDER BY created_at")
    rows = cursor.fetchall()
    conn.close()
    
    entities = []
    for row in rows:
        try:
            data = json.loads(row[0])
            entity_type_str = data.get("descriptor", {}).get("entity_type", "ABSTRACT")
            try:
                entity_type = EntityType(entity_type_str)
            except ValueError:
                entity_type = EntityType.ABSTRACT
            
            if entity_type == EntityType.ACTOR:
                entities.append(Actor.model_validate(data))
            elif entity_type == EntityType.POLITY:
                entities.append(Polity.model_validate(data))
            elif entity_type == EntityType.LOCATION:
                entities.append(Location.model_validate(data))
            else:
                entities.append(Entity.model_validate(data))
        except Exception:
            # Skip malformed entities
            continue
    
    return entities


def load_all_relationships(db_path: Path) -> list[Relationship]:
    """Load all relationships from the database.
    
    Args:
        db_path: Path to world.db
        
    Returns:
        List of all relationships
    """
    from pyscrai_core import Relationship
    
    init_harvester_tables(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT source_id, target_id, relationship_type, strength, description, data_json
        FROM relationships
        ORDER BY created_at
    """)
    rows = cursor.fetchall()
    conn.close()
    
    relationships = []
    for row in rows:
        try:
            source_id, target_id, rel_type_str, strength, description, data_json = row
            data = json.loads(data_json) if data_json else {}
            
            # Generate ID from source/target/type
            rel_id = f"rel_{source_id[:8]}_{target_id[:8]}_{rel_type_str}"
            
            from pyscrai_core import RelationshipType, RelationshipVisibility
            try:
                rel_type = RelationshipType(rel_type_str)
            except ValueError:
                rel_type = RelationshipType.CUSTOM
            
            visibility_str = data.get("visibility", "PUBLIC")
            try:
                visibility = RelationshipVisibility(visibility_str)
            except ValueError:
                visibility = RelationshipVisibility.PUBLIC
            
            relationships.append(Relationship(
                id=rel_id,
                source_id=source_id,
                target_id=target_id,
                relationship_type=rel_type,
                visibility=visibility,
                strength=strength,
                description=description or "",
                metadata=data.get("metadata", "{}"),
            ))
        except Exception:
            continue
    
    return relationships


def delete_entity(db_path: Path, entity_id: str) -> None:
    """Delete an entity and all its relationships.
    
    Args:
        db_path: Path to world.db
        entity_id: Entity ID to delete
    """
    init_harvester_tables(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Delete relationships first (foreign key constraint)
    cursor.execute("DELETE FROM relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
    
    # Delete entity
    cursor.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
    
    conn.commit()
    conn.close()


def commit_extraction_result(db_path: Path, entities: list[Entity], relationships: list[Relationship]) -> tuple[int, int]:
    """Commit a batch of entities and relationships to the database.
    
    Args:
        db_path: Path to world.db
        entities: List of entities to save
        relationships: List of relationships to save
        
    Returns:
        Tuple of (entities_saved, relationships_saved)
    """
    init_harvester_tables(db_path)
    
    for entity in entities:
        save_entity(db_path, entity)
    
    for relationship in relationships:
        save_relationship(db_path, relationship)
    
    return len(entities), len(relationships)

