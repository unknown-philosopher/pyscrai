"""DuckDB Persistence Service for PyScrAI Forge.

Stores entities and relationships for analytics and queries.

All autosave and event handlers use forge_data.duckdb (self.conn) for both writing and reading.
"""

import asyncio
import json
import logging
import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
from forge.core.event_bus import EventBus, EventPayload
from forge.core import events

logger = logging.getLogger(__name__)


class DuckDBPersistenceService:
    """Manages persistent storage of entities and relationships using DuckDB.
    
    """
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
        """Initialize main database and subscribe to autosave events."""
        # Ensure directory exists
        db_path_obj = Path(self.db_path)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        # Initialize main database connection (manual save/load and autosave)
        self.conn = duckdb.connect(self.db_path)
        self._create_schema()
        logger = __import__("logging").getLogger(__name__)
        logger.info(f"Database initialized: {self.db_path}")
        # Subscribe to graph updates - AUTO-SAVE to main database
        await self.event_bus.subscribe(
            events.TOPIC_GRAPH_UPDATED,
            self.handle_graph_updated
        )
        # Subscribe to workspace schema events - AUTO-SAVE to main database
        await self.event_bus.subscribe(
            events.TOPIC_WORKSPACE_SCHEMA,
            self.handle_workspace_schema
        )
        # Subscribe to semantic profile events - AUTO-SAVE to main database
        await self.event_bus.subscribe(
            events.TOPIC_SEMANTIC_PROFILE,
            self.handle_semantic_profile
        )
        # Subscribe to narrative events - AUTO-SAVE to main database
        await self.event_bus.subscribe(
            events.TOPIC_NARRATIVE_GENERATED,
            self.handle_narrative_generated
        )
    
    def _create_schema(self):
        """Create tables for entities and relationships in main database."""
        self._create_schema_in(self.conn)
    
    def _create_schema_in(self, conn: Optional[duckdb.DuckDBPyConnection]):
        """Create tables for entities and relationships in the specified connection."""
        if not conn:
            return
        
        # Create sequence for relationship IDs first
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS rel_seq START 1
        """)
        
        # Entities table
        conn.execute("""
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
        conn.execute("""
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
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target)
        """)
        
        # UI Artifacts table for storing workspace schemas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ui_artifacts (
                id VARCHAR PRIMARY KEY,
                schema TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ui_artifacts_created ON ui_artifacts(created_at)
        """)
        
        # Semantic Profiles table for storing entity profiles
        # Note: DuckDB doesn't support ON DELETE CASCADE in FOREIGN KEY constraints
        # The deduplication service should manually delete profiles when entities are deleted/merged
        conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_profiles (
                entity_id VARCHAR PRIMARY KEY,
                summary TEXT NOT NULL,
                key_attributes TEXT,
                related_entities TEXT,
                significance_score DOUBLE,
                profile_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_profiles_significance ON semantic_profiles(significance_score)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_profiles_entity ON semantic_profiles(entity_id)
        """)
        
        # Narratives table for storing document narratives
        conn.execute("""
            CREATE TABLE IF NOT EXISTS narratives (
                doc_id VARCHAR PRIMARY KEY,
                narrative TEXT NOT NULL,
                entity_count INTEGER,
                relationship_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_narratives_created ON narratives(created_at)
        """)
        
        conn.commit()
    
    async def handle_graph_updated(self, payload: EventPayload):
        """Persist graph updates to main database (auto-save during extraction)."""
        if not self.conn:
            return
        
        # Skip persistence if graph_stats is empty (e.g., during session restore)
        graph_stats = payload.get("graph_stats", {})
        if not graph_stats:
            return
        
        nodes = graph_stats.get("nodes", [])
        edges = graph_stats.get("edges", [])
        
        # Only persist if there are actual nodes/edges to save
        if not nodes and not edges:
            return
        
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
                    # Entity exists, update it (only if values changed to avoid unnecessary updates)
                    try:
                        self.conn.execute("""
                            UPDATE entities
                            SET type = ?, label = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ? AND (type != ? OR label != ?)
                        """, (node_type, label, node_id, node_type, label))
                    except Exception as e:
                        # Log constraint violations but don't fail - entity already exists
                        logger.debug(f"Could not update entity {node_id}: {e}")
                else:
                    # Entity doesn't exist, insert it
                    self.conn.execute("""
                        INSERT INTO entities (id, type, label)
                        VALUES (?, ?, ?)
                    """, (node_id, node_type, label))
        
        # Insert relationships (use INSERT OR IGNORE to avoid duplicates)
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            rel_type = edge.get("type")
            confidence = edge.get("confidence", 1.0)
            doc_id = edge.get("doc_id")
            if source and target and rel_type:
                # Check if relationship already exists to avoid duplicates
                existing = self.conn.execute("""
                    SELECT id FROM relationships 
                    WHERE source = ? AND target = ? AND type = ? AND doc_id = ?
                """, (source, target, rel_type, doc_id)).fetchone()
                
                if not existing:
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
    
    async def handle_workspace_schema(self, payload: EventPayload):
        """Persist workspace schema (UI artifact) to main database (auto-save)."""
        schema = payload.get("schema")
        if not schema or not self.conn:
            return
        # Generate a unique ID for this schema artifact
        # Use a hash of the schema content or timestamp-based ID
        import hashlib
        schema_json = json.dumps(schema, sort_keys=True)
        artifact_id = hashlib.md5(schema_json.encode()).hexdigest()
        # Check if this artifact already exists
        result = self.conn.execute(
            "SELECT id FROM ui_artifacts WHERE id = ?",
            (artifact_id,)
        ).fetchone()
        if not result:
            # Insert new artifact to main database
            self.conn.execute("""
                INSERT INTO ui_artifacts (id, schema)
                VALUES (?, ?)
            """, (artifact_id, schema_json))
            self.conn.commit()
    
    def store_ui_artifact(self, schema: Dict[str, Any]) -> None:
        """Manually store a UI artifact schema."""
        if not schema or not self.conn:
            return
        
        import hashlib
        schema_json = json.dumps(schema, sort_keys=True)
        artifact_id = hashlib.md5(schema_json.encode()).hexdigest()
        
        # Check if this artifact already exists
        result = self.conn.execute(
            "SELECT id FROM ui_artifacts WHERE id = ?",
            (artifact_id,)
        ).fetchone()
        
        if not result:
            self.conn.execute("""
                INSERT INTO ui_artifacts (id, schema)
                VALUES (?, ?)
            """, (artifact_id, schema_json))
            self.conn.commit()
    
    def get_stored_ui_artifacts(self) -> List[Dict[str, Any]]:
        """Retrieve all stored UI artifacts."""
        if not self.conn:
            return []
        
        result = self.conn.execute("""
            SELECT id, schema, created_at
            FROM ui_artifacts
            ORDER BY created_at ASC
        """).fetchall()
        
        artifacts = []
        for row in result:
            try:
                schema_dict = json.loads(row[1])
                artifacts.append(schema_dict)
            except json.JSONDecodeError:
                # Skip malformed JSON
                continue
        
        return artifacts
    
    async def handle_semantic_profile(self, payload: EventPayload):
        """Persist semantic profile to main database (auto-save)."""
        if not self.conn:
            return
        
        entity_id = payload.get("entity_id")
        profile = payload.get("profile")
        
        if not entity_id or not profile:
            return
        
        try:
            # Serialize profile to JSON
            profile_json = json.dumps(profile, sort_keys=True)
            
            # Extract key fields from profile for structured storage
            summary = profile.get("summary", "")
            key_attributes = json.dumps(profile.get("key_attributes", []))
            related_entities = json.dumps(profile.get("related_entities", []))
            significance_score = profile.get("significance_score", 0.0)
            
            # Upsert profile (insert if new, update if exists)
            # Check if profile exists
            existing = self.conn.execute(
                "SELECT entity_id FROM semantic_profiles WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            
            if existing:
                # Update existing profile
                self.conn.execute("""
                    UPDATE semantic_profiles SET
                        summary = ?,
                        key_attributes = ?,
                        related_entities = ?,
                        significance_score = ?,
                        profile_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE entity_id = ?
                """, (summary, key_attributes, related_entities, significance_score, profile_json, entity_id))
            else:
                # Insert new profile
                self.conn.execute("""
                    INSERT INTO semantic_profiles 
                        (entity_id, summary, key_attributes, related_entities, significance_score, profile_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (entity_id, summary, key_attributes, related_entities, significance_score, profile_json))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error persisting semantic profile for {entity_id}: {e}")
            if self.conn:
                self.conn.rollback()
    
    async def handle_narrative_generated(self, payload: EventPayload):
        """Persist narrative to main database (auto-save)."""
        if not self.conn:
            return
        
        doc_id = payload.get("doc_id")
        narrative = payload.get("narrative")
        entity_count = payload.get("entity_count", 0)
        relationship_count = payload.get("relationship_count", 0)
        
        if not doc_id or not narrative:
            return
        
        try:
            # Upsert narrative (insert if new, update if exists)
            # Check if narrative exists
            existing = self.conn.execute(
                "SELECT doc_id FROM narratives WHERE doc_id = ?",
                (doc_id,)
            ).fetchone()
            
            if existing:
                # Update existing narrative
                self.conn.execute("""
                    UPDATE narratives SET
                        narrative = ?,
                        entity_count = ?,
                        relationship_count = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE doc_id = ?
                """, (narrative, entity_count, relationship_count, doc_id))
            else:
                # Insert new narrative
                self.conn.execute("""
                    INSERT INTO narratives 
                        (doc_id, narrative, entity_count, relationship_count)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, narrative, entity_count, relationship_count))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error persisting narrative for {doc_id}: {e}")
            if self.conn:
                self.conn.rollback()
    
    def get_semantic_profile(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a semantic profile for an entity."""
        if not self.conn:
            return None
        
        try:
            result = self.conn.execute("""
                SELECT profile_json
                FROM semantic_profiles
                WHERE entity_id = ?
            """, (entity_id,)).fetchone()
            
            if result:
                return json.loads(result[0])
        except Exception as e:
            logger.error(f"Error retrieving semantic profile for {entity_id}: {e}")
        
        return None
    
    def get_all_semantic_profiles(self) -> List[Dict[str, Any]]:
        """Retrieve all semantic profiles."""
        if not self.conn:
            return []
        
        profiles = []
        try:
            results = self.conn.execute("""
                SELECT entity_id, profile_json
                FROM semantic_profiles
                ORDER BY significance_score DESC
            """).fetchall()
            
            for row in results:
                try:
                    profile = json.loads(row[1])
                    profile["entity_id"] = row[0]  # Add entity_id to profile
                    profiles.append(profile)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Error retrieving semantic profiles: {e}")
        
        return profiles
    
    def get_narrative(self, doc_id: str) -> Optional[str]:
        """Retrieve a narrative for a document."""
        if not self.conn:
            return None
        
        try:
            result = self.conn.execute("""
                SELECT narrative
                FROM narratives
                WHERE doc_id = ?
            """, (doc_id,)).fetchone()
            
            if result:
                return result[0]
        except Exception as e:
            logger.error(f"Error retrieving narrative for {doc_id}: {e}")
        
        return None
    
    def get_all_narratives(self) -> List[Dict[str, Any]]:
        """Retrieve all narratives."""
        if not self.conn:
            return []
        
        narratives = []
        try:
            results = self.conn.execute("""
                SELECT doc_id, narrative, entity_count, relationship_count, created_at
                FROM narratives
                ORDER BY created_at DESC
            """).fetchall()
            
            for row in results:
                narratives.append({
                    "doc_id": row[0],
                    "narrative": row[1],
                    "entity_count": row[2],
                    "relationship_count": row[3],
                    "created_at": row[4],
                })
        except Exception as e:
            logger.error(f"Error retrieving narratives: {e}")
        
        return narratives
    
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
        
        logger = __import__("logging").getLogger(__name__)
        try:
            # Delete in order to respect foreign key constraints:
            # 1. Delete semantic_profiles first (has foreign key to entities)
            self.conn.execute("DELETE FROM semantic_profiles")
            # 2. Delete narratives (no foreign keys, but clear it)
            self.conn.execute("DELETE FROM narratives")
            # 3. Delete relationships (has foreign keys to entities)
            self.conn.execute("DELETE FROM relationships")
            # 4. Delete entities (now safe since nothing references them)
            self.conn.execute("DELETE FROM entities")
            # 5. Delete UI artifacts (no foreign keys)
            self.conn.execute("DELETE FROM ui_artifacts")
            # Note: DuckDB doesn't support ALTER SEQUENCE RESTART yet
            # The sequence will continue from its current value, which is fine
            # for our use case since we're using it for relationship IDs
            self.conn.commit()
            
            # CRITICAL: Force a checkpoint to ensure WAL is flushed to main database file
            # This prevents the cleared state from being lost if the connection closes unexpectedly
            try:
                self.conn.execute("CHECKPOINT")
                logger.info("Database checkpoint completed after clearing data")
            except Exception as e:
                logger.warning(f"Could not checkpoint database after clearing: {e}")
            
            logger.info("Database cleared: all entities, relationships, profiles, narratives, and UI artifacts removed")
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            # DuckDB doesn't require explicit rollback for most operations
            # Only rollback if there's an active transaction
            try:
                self.conn.rollback()
            except Exception:
                # If rollback fails, just continue - the transaction may not be active
                pass
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
