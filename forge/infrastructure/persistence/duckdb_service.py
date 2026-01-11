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
        self.db_path = db_path or "forge_data.duckdb"
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
    
    async def start(self):
        """Initialize database schema and subscribe to graph events."""
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
        
        # Insert/update entities
        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("type")
            label = node.get("label")
            
            if node_id and node_type and label:
                # Upsert entity
                self.conn.execute("""
                    INSERT INTO entities (id, type, label)
                    VALUES (?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET
                        type = EXCLUDED.type,
                        label = EXCLUDED.label,
                        updated_at = NOW()
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
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
