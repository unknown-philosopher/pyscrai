"""
Database Manager for Forge 3.0.

Manages the world.db SQLite database with full CRUD operations
for entities and relationships, plus event logging.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forge.core.models.entity import Entity, EntityType
from forge.core.models.relationship import Relationship, RelationType
from forge.core.events.base import BaseEvent, EventType


# ============================================================================
# Database Manager
# ============================================================================


class DatabaseManager:
    """Manages the world.db SQLite database.
    
    Provides CRUD operations for entities and relationships,
    event logging for the Sentinel, and query utilities.
    
    Usage:
        db = DatabaseManager(project_path / "world.db")
        
        # Save an entity
        db.save_entity(entity)
        
        # Query entities
        actors = db.get_entities_by_type(EntityType.ACTOR)
        
        # Log an event
        db.log_event(event)
    """
    
    def __init__(self, db_path: str | Path):
        """Initialize the database manager.
        
        Args:
            db_path: Path to the world.db SQLite database
        """
        self.db_path = Path(db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize(self) -> None:
        """Initialize the database schema.
        
        Creates all required tables if they don't exist.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                aliases_json TEXT DEFAULT '[]',
                tags_json TEXT DEFAULT '[]',
                attributes_json TEXT DEFAULT '{}',
                location_id TEXT,
                region_id TEXT,
                coordinates_json TEXT,
                layer TEXT DEFAULT 'terrestrial',
                source_documents_json TEXT DEFAULT '[]',
                embedding_row_id INTEGER,
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
                label TEXT DEFAULT '',
                description TEXT DEFAULT '',
                strength REAL DEFAULT 1.0,
                visibility TEXT DEFAULT 'public',
                attributes_json TEXT DEFAULT '{}',
                source_documents_json TEXT DEFAULT '[]',
                embedding_row_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
        """)
        
        # Events log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events_log (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source_id TEXT,
                target_id TEXT,
                description TEXT DEFAULT '',
                data_json TEXT DEFAULT '{}',
                source_document TEXT,
                is_rolled_back INTEGER DEFAULT 0
            )
        """)
        
        # Schema metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events_log(event_type)")
        
        conn.commit()
        conn.close()
    
    # ========== Entity Operations ==========
    
    def save_entity(self, entity: Entity) -> None:
        """Save or update an entity in the database.
        
        Args:
            entity: Entity to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO entities (
                id, entity_type, name, description,
                aliases_json, tags_json, attributes_json,
                location_id, region_id, coordinates_json, layer,
                source_documents_json, embedding_row_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id,
            entity.entity_type.value,
            entity.name,
            entity.description,
            json.dumps(entity.aliases),
            json.dumps(entity.tags),
            json.dumps(entity.attributes),
            entity.location_id,
            entity.region_id,
            json.dumps(list(entity.coordinates)) if entity.coordinates else None,
            entity.layer.value,
            json.dumps(entity.source_documents),
            entity.embedding_row_id,
            entity.created_at.isoformat(),
            entity.updated_at.isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    def get_entity(self, entity_id: str) -> Entity | None:
        """Get an entity by ID.
        
        Args:
            entity_id: Entity ID to look up
            
        Returns:
            Entity if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return self._row_to_entity(row)
    
    def get_all_entities(self) -> list[Entity]:
        """Get all entities in the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM entities ORDER BY created_at")
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_entity(row) for row in rows]
    
    def get_entities_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of a specific type."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM entities WHERE entity_type = ? ORDER BY name",
            (entity_type.value,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_entity(row) for row in rows]
    
    def search_entities(self, query: str) -> list[Entity]:
        """Search entities by name or description."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        pattern = f"%{query}%"
        cursor.execute("""
            SELECT * FROM entities
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY name
        """, (pattern, pattern))
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_entity(row) for row in rows]
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity by ID.
        
        Args:
            entity_id: Entity to delete
            
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert a database row to an Entity object."""
        coords = json.loads(row["coordinates_json"]) if row["coordinates_json"] else None
        
        return Entity(
            id=row["id"],
            entity_type=EntityType(row["entity_type"]),
            name=row["name"],
            description=row["description"],
            aliases=json.loads(row["aliases_json"]),
            tags=json.loads(row["tags_json"]),
            attributes=json.loads(row["attributes_json"]),
            location_id=row["location_id"],
            region_id=row["region_id"],
            coordinates=tuple(coords) if coords else None,
            layer=row["layer"],
            source_documents=json.loads(row["source_documents_json"]),
            embedding_row_id=row["embedding_row_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    # ========== Relationship Operations ==========
    
    def save_relationship(self, relationship: Relationship) -> None:
        """Save or update a relationship in the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO relationships (
                id, source_id, target_id, relationship_type,
                label, description, strength, visibility,
                attributes_json, source_documents_json, embedding_row_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            relationship.id,
            relationship.source_id,
            relationship.target_id,
            relationship.relationship_type.value,
            relationship.label,
            relationship.description,
            relationship.strength,
            relationship.visibility.value,
            json.dumps(relationship.attributes),
            json.dumps(relationship.source_documents),
            relationship.embedding_row_id,
            relationship.created_at.isoformat(),
            relationship.updated_at.isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    def get_relationship(self, relationship_id: str) -> Relationship | None:
        """Get a relationship by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM relationships WHERE id = ?", (relationship_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return self._row_to_relationship(row)
    
    def get_all_relationships(self) -> list[Relationship]:
        """Get all relationships in the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM relationships ORDER BY created_at")
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_relationship(row) for row in rows]
    
    def get_relationships_for_entity(self, entity_id: str) -> list[Relationship]:
        """Get all relationships involving an entity (as source or target)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM relationships
            WHERE source_id = ? OR target_id = ?
            ORDER BY created_at
        """, (entity_id, entity_id))
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_relationship(row) for row in rows]
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        """Convert a database row to a Relationship object."""
        return Relationship(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relationship_type=RelationType(row["relationship_type"]),
            label=row["label"],
            description=row["description"],
            strength=row["strength"],
            visibility=row["visibility"],
            attributes=json.loads(row["attributes_json"]),
            source_documents=json.loads(row["source_documents_json"]),
            embedding_row_id=row["embedding_row_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    # ========== Event Logging ==========
    
    def log_event(self, event: BaseEvent) -> None:
        """Log an event to the events table."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO events_log (
                id, event_type, timestamp, source_id, target_id,
                description, data_json, source_document, is_rolled_back
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.id,
            event.event_type.value,
            event.timestamp.isoformat(),
            event.source_id,
            event.target_id,
            event.description,
            json.dumps(event.data),
            event.source_document,
            1 if event.is_rolled_back else 0,
        ))
        
        conn.commit()
        conn.close()
    
    def get_events(
        self,
        limit: int = 100,
        event_type: EventType | None = None,
        include_rolled_back: bool = False,
    ) -> list[dict[str, Any]]:
        """Get events from the log.
        
        Args:
            limit: Maximum number of events to return
            event_type: Optional filter by event type
            include_rolled_back: Whether to include rolled-back events
            
        Returns:
            List of event dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM events_log WHERE 1=1"
        params = []
        
        if not include_rolled_back:
            query += " AND is_rolled_back = 0"
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def rollback_event(self, event_id: str) -> bool:
        """Mark an event as rolled back.
        
        Args:
            event_id: Event to roll back
            
        Returns:
            True if updated, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE events_log SET is_rolled_back = 1 WHERE id = ?",
            (event_id,)
        )
        updated = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return updated
    
    # ========== Statistics ==========
    
    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM relationships")
        relationship_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM events_log WHERE is_rolled_back = 0")
        event_count = cursor.fetchone()[0]
        
        # Count by entity type
        cursor.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM entities
            GROUP BY entity_type
        """)
        type_counts = {row["entity_type"]: row["count"] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "entities": entity_count,
            "relationships": relationship_count,
            "events": event_count,
            "entities_by_type": type_counts,
        }
