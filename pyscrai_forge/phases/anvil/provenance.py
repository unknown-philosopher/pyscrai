"""Phase 5: ANVIL - Provenance Tracking.

The ProvenanceTracker records attribute changes over time,
maintaining a complete history of entity modifications.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from pyscrai_core import Entity

logger = logging.getLogger(__name__)


@dataclass
class AttributeChange:
    """A recorded attribute change."""
    id: int
    entity_id: str
    attribute: str
    old_value: Optional[str]
    new_value: Optional[str]
    source: str  # 'user' or 'agent:scout', etc.
    turn_id: Optional[int]
    timestamp: str
    
    @classmethod
    def from_db_row(cls, row: tuple) -> "AttributeChange":
        """Create from database row."""
        return cls(
            id=row[0],
            entity_id=row[1],
            attribute=row[2],
            old_value=row[3],
            new_value=row[4],
            source=row[5] or "user",
            turn_id=row[6],
            timestamp=row[7]
        )


class ProvenanceTracker:
    """Tracks attribute changes for entities over time.
    
    Uses the attribute_history table in world.db to maintain
    a complete audit trail of all modifications.
    """
    
    def __init__(self, db_path: Path):
        """Initialize the provenance tracker.
        
        Args:
            db_path: Path to the world.db database
        """
        self.db_path = Path(db_path)
        self._ensure_table()
    
    def _ensure_table(self) -> None:
        """Ensure the attribute_history table exists."""
        if not self.db_path.exists():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attribute_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    source TEXT DEFAULT 'user',
                    turn_id INTEGER,
                    timestamp TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_attribute_history_entity 
                ON attribute_history(entity_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_attribute_history_timestamp 
                ON attribute_history(timestamp)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def record_change(
        self,
        entity_id: str,
        attribute: str,
        old_value: Optional[str],
        new_value: Optional[str],
        source: str = "user",
        turn_id: Optional[int] = None
    ) -> int:
        """Record an attribute change.
        
        Args:
            entity_id: ID of the entity being modified
            attribute: Name of the attribute being changed
            old_value: Previous value (None for new attributes)
            new_value: New value (None for deletions)
            source: Source of the change ('user', 'agent:scout', etc.)
            turn_id: Optional turn/session ID for grouping changes
            
        Returns:
            ID of the created history record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.now(UTC).isoformat()
            
            cursor.execute("""
                INSERT INTO attribute_history 
                (entity_id, attribute, old_value, new_value, source, turn_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (entity_id, attribute, old_value, new_value, source, turn_id, timestamp))
            
            record_id = cursor.lastrowid
            conn.commit()
            
            logger.debug(f"Recorded change for {entity_id}.{attribute}: '{old_value}' -> '{new_value}'")
            return record_id
            
        finally:
            conn.close()
    
    def record_entity_changes(
        self,
        old_entity: Optional["Entity"],
        new_entity: "Entity",
        source: str = "user",
        turn_id: Optional[int] = None
    ) -> List[int]:
        """Record all attribute changes between entity versions.
        
        Args:
            old_entity: Previous entity state (None for new entities)
            new_entity: New entity state
            source: Source of the changes
            turn_id: Optional turn ID
            
        Returns:
            List of created record IDs
        """
        record_ids = []
        
        # Get old and new attribute values
        old_attrs = self._entity_to_attrs(old_entity) if old_entity else {}
        new_attrs = self._entity_to_attrs(new_entity)
        
        # Find changes
        all_attrs = set(old_attrs.keys()) | set(new_attrs.keys())
        
        for attr in all_attrs:
            old_val = old_attrs.get(attr)
            new_val = new_attrs.get(attr)
            
            if old_val != new_val:
                record_id = self.record_change(
                    entity_id=new_entity.id,
                    attribute=attr,
                    old_value=old_val,
                    new_value=new_val,
                    source=source,
                    turn_id=turn_id
                )
                record_ids.append(record_id)
        
        return record_ids
    
    def _entity_to_attrs(self, entity: "Entity") -> Dict[str, str]:
        """Extract attributes from entity as string dict."""
        attrs = {}
        
        if hasattr(entity, "id"):
            attrs["id"] = entity.id
        
        if hasattr(entity, "descriptor"):
            desc = entity.descriptor
            if hasattr(desc, "name"):
                attrs["name"] = desc.name
            if hasattr(desc, "description"):
                attrs["description"] = desc.description or ""
            if hasattr(desc, "entity_type"):
                attrs["entity_type"] = str(desc.entity_type.value if hasattr(desc.entity_type, "value") else desc.entity_type)
            if hasattr(desc, "aliases"):
                attrs["aliases"] = json.dumps(desc.aliases or [])
        
        # Add other components as needed
        
        return attrs
    
    def get_entity_history(
        self,
        entity_id: str,
        limit: Optional[int] = None
    ) -> List[AttributeChange]:
        """Get change history for an entity.
        
        Args:
            entity_id: Entity ID to get history for
            limit: Maximum number of records to return
            
        Returns:
            List of changes, most recent first
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT id, entity_id, attribute, old_value, new_value, 
                       source, turn_id, timestamp
                FROM attribute_history
                WHERE entity_id = ?
                ORDER BY timestamp DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, (entity_id,))
            rows = cursor.fetchall()
            
            return [AttributeChange.from_db_row(row) for row in rows]
            
        finally:
            conn.close()
    
    def get_attribute_history(
        self,
        entity_id: str,
        attribute: str
    ) -> List[AttributeChange]:
        """Get change history for a specific attribute.
        
        Args:
            entity_id: Entity ID
            attribute: Attribute name
            
        Returns:
            List of changes, most recent first
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, entity_id, attribute, old_value, new_value,
                       source, turn_id, timestamp
                FROM attribute_history
                WHERE entity_id = ? AND attribute = ?
                ORDER BY timestamp DESC
            """, (entity_id, attribute))
            
            rows = cursor.fetchall()
            return [AttributeChange.from_db_row(row) for row in rows]
            
        finally:
            conn.close()
    
    def get_recent_changes(
        self,
        limit: int = 50,
        source_filter: Optional[str] = None
    ) -> List[AttributeChange]:
        """Get recent changes across all entities.
        
        Args:
            limit: Maximum number of records
            source_filter: Optional filter by source
            
        Returns:
            List of recent changes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if source_filter:
                cursor.execute("""
                    SELECT id, entity_id, attribute, old_value, new_value,
                           source, turn_id, timestamp
                    FROM attribute_history
                    WHERE source = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (source_filter, limit))
            else:
                cursor.execute("""
                    SELECT id, entity_id, attribute, old_value, new_value,
                           source, turn_id, timestamp
                    FROM attribute_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [AttributeChange.from_db_row(row) for row in rows]
            
        finally:
            conn.close()
    
    def get_turn_changes(self, turn_id: int) -> List[AttributeChange]:
        """Get all changes from a specific turn/session.
        
        Args:
            turn_id: Turn ID to filter by
            
        Returns:
            List of changes from that turn
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, entity_id, attribute, old_value, new_value,
                       source, turn_id, timestamp
                FROM attribute_history
                WHERE turn_id = ?
                ORDER BY timestamp
            """, (turn_id,))
            
            rows = cursor.fetchall()
            return [AttributeChange.from_db_row(row) for row in rows]
            
        finally:
            conn.close()
    
    def revert_change(self, change_id: int) -> bool:
        """Revert a specific change.
        
        Note: This creates a new history record, not a deletion.
        
        Args:
            change_id: ID of the change to revert
            
        Returns:
            True if successful
        """
        # Get the change
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT entity_id, attribute, old_value, new_value
                FROM attribute_history
                WHERE id = ?
            """, (change_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            entity_id, attribute, old_value, new_value = row
            
            # Record a reverting change
            self.record_change(
                entity_id=entity_id,
                attribute=attribute,
                old_value=new_value,  # Swap old and new
                new_value=old_value,
                source="user:revert"
            )
            
            return True
            
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict:
        """Get provenance statistics.
        
        Returns:
            Dict with change statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Total changes
            cursor.execute("SELECT COUNT(*) FROM attribute_history")
            total = cursor.fetchone()[0]
            
            # Changes by source
            cursor.execute("""
                SELECT source, COUNT(*) 
                FROM attribute_history 
                GROUP BY source
            """)
            by_source = dict(cursor.fetchall())
            
            # Changes by attribute
            cursor.execute("""
                SELECT attribute, COUNT(*) 
                FROM attribute_history 
                GROUP BY attribute
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            by_attribute = dict(cursor.fetchall())
            
            # Entities with most changes
            cursor.execute("""
                SELECT entity_id, COUNT(*) 
                FROM attribute_history 
                GROUP BY entity_id
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            by_entity = dict(cursor.fetchall())
            
            return {
                "total_changes": total,
                "by_source": by_source,
                "top_attributes": by_attribute,
                "top_entities": by_entity
            }
            
        finally:
            conn.close()

