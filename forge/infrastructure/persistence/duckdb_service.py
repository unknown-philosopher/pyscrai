"""DuckDB Persistence Service for PyScrAI Forge.

Stores entities and relationships for analytics and queries.
"""

import asyncio
import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
from forge.core.event_bus import EventBus, EventPayload
from forge.core import events


class DuckDBPersistenceService:
    """Manages persistent storage of entities and relationships using DuckDB."""
    
    def __init__(self, event_bus: EventBus, db_path: Optional[str] = None):
        self.event_bus = event_bus
        # Default to data/db/forge_data.duckdb relative to project root
        if db_path is None:
            # Get project root (assuming this file is in forge/infrastructure/persistence/)
            project_root = Path(__file__).parent.parent.parent.parent
            db_dir = project_root / "data" / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "forge_data.duckdb")
        else:
            self.db_path = db_path
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
    
    async def start(self):
        """Initialize database schema and subscribe to graph events."""
        # Ensure directory exists
        db_path_obj = Path(self.db_path)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database connection
        self.conn = duckdb.connect(self.db_path)
        self._create_schema()
        
        # Subscribe to graph update events
        await self.event_bus.subscribe(
            events.TOPIC_GRAPH_UPDATED,
            self.handle_graph_updated
        )
    
    def _create_schema(self):
        """Create tables for entities and relationships."""
        if not self.conn:
            return
        
        # Create sequence for relationship IDs first
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS rel_seq START 1
        """)
        
        # Entities table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id VARCHAR PRIMARY KEY,
                type VARCHAR NOT NULL,
                label VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Relationships table
        # Note: DuckDB doesn't support ON DELETE CASCADE in FOREIGN KEY constraints
        # The deduplication service manually updates relationships before deleting entities
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY DEFAULT nextval('rel_seq'),
                source VARCHAR NOT NULL,
                target VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                confidence DOUBLE NOT NULL,
                doc_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source) REFERENCES entities(id),
                FOREIGN KEY (target) REFERENCES entities(id)
            )
        """)
        
        # Create indexes for performance
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target)
        """)
        
        self.conn.commit()
    
    async def handle_graph_updated(self, payload: EventPayload):
        """Persist graph updates to DuckDB."""
        if not self.conn:
            return
        
        graph_stats = payload.get("graph_stats", {})
        nodes = graph_stats.get("nodes", [])
        edges = graph_stats.get("edges", [])
        
        # Upsert entities (insert if new, update if exists)
        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("type")
            label = node.get("label")
            
            if node_id and node_type and label:
                # Check if entity already exists
                result = self.conn.execute(
                    "SELECT id FROM entities WHERE id = ?",
                    (node_id,)
                ).fetchone()
                
                if result:
                    # Entity exists, update it
                    self.conn.execute("""
                        UPDATE entities
                        SET type = ?, label = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (node_type, label, node_id))
                else:
                    # Entity doesn't exist, insert it
                    self.conn.execute("""
                        INSERT INTO entities (id, type, label)
                        VALUES (?, ?, ?)
                    """, (node_id, node_type, label))
        
        # Insert relationships (append only for now)
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            rel_type = edge.get("type")
            confidence = edge.get("confidence", 1.0)
            doc_id = edge.get("doc_id")
            
            if source and target and rel_type:
                self.conn.execute("""
                    INSERT INTO relationships (source, target, type, confidence, doc_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (source, target, rel_type, confidence, doc_id))
        
        self.conn.commit()
        
        # Emit AG-UI event with persistence confirmation
        entity_count = self.get_entity_count()
        relationship_count = self.get_relationship_count()
        
        await self.event_bus.publish(
            events.TOPIC_AGUI_EVENT,
            events.create_agui_event(
                f"✅ Persisted {len(nodes)} entities, {len(edges)} relationships | "
                f"Total: {entity_count} entities, {relationship_count} relationships",
                level="success"
            )
        )
    
    def get_entity_count(self) -> int:
        """Get total number of entities in the database."""
        if not self.conn:
            return 0
        result = self.conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        return result[0] if result else 0
    
    def get_relationship_count(self) -> int:
        """Get total number of relationships in the database."""
        if not self.conn:
            return 0
        result = self.conn.execute("SELECT COUNT(*) FROM relationships").fetchone()
        return result[0] if result else 0
    
    def get_all_entities(self) -> List[Dict[str, Any]]:
        """Retrieve all entities."""
        if not self.conn:
            return []
        result = self.conn.execute("""
            SELECT id, type, label, created_at, updated_at
            FROM entities
            ORDER BY created_at DESC
        """).fetchall()
        
        return [
            {
                "id": row[0],
                "type": row[1],
                "label": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            }
            for row in result
        ]
    
    def get_all_relationships(self) -> List[Dict[str, Any]]:
        """Retrieve all relationships."""
        if not self.conn:
            return []
        result = self.conn.execute("""
            SELECT id, source, target, type, confidence, doc_id, created_at
            FROM relationships
            ORDER BY created_at DESC
        """).fetchall()
        
        return [
            {
                "id": row[0],
                "source": row[1],
                "target": row[2],
                "type": row[3],
                "confidence": row[4],
                "doc_id": row[5],
                "created_at": row[6],
            }
            for row in result
        ]
    
    def clear_all_data(self):
        """Clear all entities and relationships from the database."""
        if not self.conn:
            return
        
        try:
            # Delete relationships first (due to foreign key constraints)
            self.conn.execute("DELETE FROM relationships")
            # Then delete entities
            self.conn.execute("DELETE FROM entities")
            # Reset sequence
            self.conn.execute("ALTER SEQUENCE rel_seq RESTART WITH 1")
            self.conn.commit()
            logger = __import__("logging").getLogger(__name__)
            logger.info("Database cleared: all entities and relationships removed")
        except Exception as e:
            logger = __import__("logging").getLogger(__name__)
            logger.error(f"Error clearing database: {e}")
            if self.conn:
                self.conn.rollback()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
