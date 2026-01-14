"""Session Manager for saving, loading, and clearing application state."""

from __future__ import annotations

import logging
import asyncio
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from forge.core import events

if TYPE_CHECKING:
    from forge.core.app_controller import AppController
    from forge.infrastructure.persistence.duckdb_service import DuckDBPersistenceService
    from forge.infrastructure.vector.qdrant_service import QdrantService
    from forge.infrastructure.embeddings.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SessionManager:
    """Orchestrates loading persisted state into the runtime."""

    def __init__(
        self,
        controller: "AppController",
        persistence_service: "DuckDBPersistenceService",
        qdrant_service: "QdrantService",
        embedding_service: "EmbeddingService"
    ):
        self.controller = controller
        self.persistence = persistence_service
        self.qdrant = qdrant_service
        self.embedding = embedding_service

    async def restore_session(self):
        """Reloads UI state and re-indexes vectors from the last manually-saved project.
        
        NOTE: Since auto-save is disabled, this loads the state from the last time
        the user clicked 'Save Project'. Real-time extraction/analysis changes are
        held in memory until explicitly saved.
        
        NOTE: UI artifacts are NOT restored - they are snapshots from previous extractions
        and may be stale. The workspace should be empty, allowing intelligence views
        to query the database directly for current data.
        """
        logger.info("♻️ Restoring session from database...")
        await self.controller.push_agui_log("♻️ Starting Session Restore...", "info")
        
        # 1. Clear current UI first to avoid duplicates
        self.controller.clear_workspace()

        # 2. Skip restoring UI artifacts - they are snapshots from previous extractions
        # and may be stale. The workspace should be empty, allowing intelligence views
        # (Graph Analytics, Entity Cards, etc.) to query the database directly for current data.
        # UI artifacts are meant for real-time streaming during extraction, not persistent storage.
        logger.info("Skipping UI artifacts restoration (workspace will be empty, views query DB directly)")
        await self.controller.push_agui_log("Workspace cleared. Intelligence views will load from database.", "info")

        # 3. Clear QDrant collections before re-indexing to avoid IndexError
        logger.info("Clearing QDrant collections before re-indexing...")
        await self.controller.push_agui_log("Clearing vector store...", "info")
        await self.qdrant.clear_collections()

        # 4. Re-index Entities
        entities = self.persistence.get_all_entities()
        if entities:
            msg = f"Re-indexing {len(entities)} entities into Vector Store..."
            logger.info(msg)
            await self.controller.push_agui_log(msg, "info")
            
            # Convert database format to entity format for embedding
            # Database has: id, type, label, created_at, updated_at
            # Embedding format needs: text, type (for entity dict)
            entity_list = [
                {
                    "text": entity["label"],
                    "type": entity["type"]
                }
                for entity in entities
            ]
            
            # Prepare texts for embedding (same format as EmbeddingService)
            entity_texts = [
                f"{entity['text']} ({entity['type']})"
                for entity in entity_list
            ]
            
            # Embed entities directly (bypass extraction pipeline)
            embeddings = await self.embedding.embed_batch(entity_texts, use_long_context=False)
            
            # Publish embedded events directly (only QdrantService listens to these)
            for entity, embedding_vec in zip(entity_list, embeddings):
                await self.controller.publish(
                    events.TOPIC_ENTITY_EMBEDDED,
                    {
                        "doc_id": "restore_session",
                        "entity": entity,
                        "text": f"{entity['text']} ({entity['type']})",
                        "embedding": embedding_vec,
                        "dimension": len(embedding_vec),
                    }
                )
            
            await self.controller.push_agui_log("Entity re-indexing complete.", "success")
        else:
            await self.controller.push_agui_log("No entities found to re-index.", "warning")

        # 5. Re-index Relationships
        relationships = self.persistence.get_all_relationships()
        if relationships:
            msg = f"Re-indexing {len(relationships)} relationships into Vector Store..."
            logger.info(msg)
            await self.controller.push_agui_log(msg, "info")
            
            # Convert database format to relationship format for embedding
            # Database has: id, source, target, type, confidence, doc_id, created_at
            # Embedding format needs: source, target, type
            relationship_list = [
                {
                    "source": rel["source"],
                    "target": rel["target"],
                    "type": rel["type"]
                }
                for rel in relationships
            ]
            
            # Prepare texts for embedding (same format as EmbeddingService)
            relationship_texts = [
                f"{rel['source']} {rel['type']} {rel['target']}"
                for rel in relationship_list
            ]
            
            # Embed relationships directly (bypass extraction pipeline)
            embeddings = await self.embedding.embed_batch(relationship_texts, use_long_context=False)
            
            # Publish embedded events directly (only QdrantService listens to these)
            for rel, embedding_vec in zip(relationship_list, embeddings):
                await self.controller.publish(
                    events.TOPIC_RELATIONSHIP_EMBEDDED,
                    {
                        "doc_id": "restore_session",
                        "relationship": rel,
                        "text": f"{rel['source']} {rel['type']} {rel['target']}",
                        "embedding": embedding_vec,
                        "dimension": len(embedding_vec),
                    }
                )
            
            await self.controller.push_agui_log("Relationship re-indexing complete.", "success")
        else:
            await self.controller.push_agui_log("No relationships found to re-index.", "warning")
        
        # 6. Load semantic profiles from database and publish to workspace
        profiles = self.persistence.get_all_semantic_profiles()
        if profiles:
            logger.info(f"Loading {len(profiles)} semantic profiles from database...")
            # Get all entities once (avoid O(n*m) complexity)
            entities = self.persistence.get_all_entities()
            entity_map = {e["id"]: e for e in entities}  # Create lookup map
            
            for profile in profiles:
                entity_id = profile.get("entity_id")
                if entity_id:
                    # Get entity info for display
                    entity_info = entity_map.get(entity_id)
                    if entity_info:
                        await self.controller.publish(
                            events.TOPIC_WORKSPACE_SCHEMA,
                            events.create_workspace_schema_event({
                                "type": "semantic_profile",
                                "title": f"Profile: {entity_info['label']}",
                                "props": profile
                            })
                        )
            await self.controller.push_agui_log(f"Loaded {len(profiles)} semantic profiles from database.", "info")
        else:
            await self.controller.push_agui_log("No semantic profiles found in database.", "info")
        
        # 7. Load narratives from database and publish to workspace
        narratives = self.persistence.get_all_narratives()
        if narratives:
            logger.info(f"Loading {len(narratives)} narratives from database...")
            for narrative_data in narratives:
                await self.controller.publish(
                    events.TOPIC_WORKSPACE_SCHEMA,
                    events.create_workspace_schema_event({
                        "type": "narrative",
                        "title": f"Narrative: {narrative_data['doc_id']}",
                        "props": {
                            "doc_id": narrative_data["doc_id"],
                            "narrative": narrative_data["narrative"],
                            "entity_count": narrative_data["entity_count"],
                            "relationship_count": narrative_data["relationship_count"],
                        }
                    })
                )
            await self.controller.push_agui_log(f"Loaded {len(narratives)} narratives from database.", "info")
        
        # 8. Trigger graph analysis to generate UI schemas from database data
        # This will cause AdvancedGraphAnalysisService to analyze the graph and publish schemas
        # Pass None as doc_id to analyze ALL entities/relationships, not just a specific document
        # Set skip_deduplication=True since data is already deduplicated
        logger.info("Triggering graph analysis to generate UI schemas...")
        await self.controller.push_agui_log("Generating intelligence views from database...", "info")
        await self.controller.publish(
            events.TOPIC_GRAPH_UPDATED,
            {
                "doc_id": None,  # None = analyze all data, not filtered by doc_id
                "graph_stats": {},  # Empty stats - services will query DB directly
                "skip_deduplication": True,  # Skip deduplication during restore (data already processed)
                "skip_semantic_profiling": True  # Skip semantic profiling (profiles already loaded from DB)
            }
        )

    async def clear_workspace_only(self):
        """Clears only the UI workspace for a new project (database untouched)."""
        logger.info("🎨 Clearing workspace UI only...")
        
        # Clear only the UI workspace, keep all database data intact
        self.controller.clear_workspace()
        
        await self.controller.push_agui_log("Workspace cleared. Database preserved.", "success")

    async def clear_session(self):
        """Wipes the database and clears the UI (full reset)."""
        logger.info("🗑️ Clearing session...")
        
        # 1. Clear UI
        self.controller.clear_workspace()
        
        # 2. Clear Database
        self.persistence.clear_all_data()
        
        # 3. Reset the database connection to ensure fresh state
        # This prevents cached state or pending transactions from interfering
        try:
            if self.persistence.conn:
                self.persistence.conn.close()
                logger.info("Closed database connection after clearing")
            
            # Reconnect to get a fresh connection
            import duckdb
            self.persistence.conn = duckdb.connect(self.persistence.db_path)
            # Recreate schema to ensure tables exist
            self.persistence._create_schema()
            logger.info("Reconnected to database with fresh state")
        except Exception as e:
            logger.error(f"Error resetting database connection: {e}")
            await self.controller.push_agui_log(f"Warning: Database connection reset failed: {e}", "warning")
        
        # 4. Clear Vector Store (if supported by QdrantService, otherwise restart needed for in-memory)
        # Assuming QdrantService has a way to reset or we just rely on DB wipe
        # Re-creating collections in Qdrant is a heavy op, ideally we'd delete points.
        # For now, we rely on the DB wipe. Future searches won't match if we don't clear vectors,
        # but semantic deduplication logic will just fail to find matches (safe).
        
        await self.controller.push_agui_log("Session and Database Cleared.", "success")

    async def save_project(self, file_path: str) -> None:
        """Save the current project database to the specified file path."""
        logger.info(f"💾 Saving project to {file_path}...")
        await self.controller.push_agui_log(f"Saving project to {file_path}...", "info")
        
        try:
            # Ensure all transactions are committed and WAL is checkpointed
            if self.persistence.conn:
                # Force a checkpoint to write WAL data to the main database file
                try:
                    self.persistence.conn.execute("CHECKPOINT")
                except Exception as e:
                    logger.warning(f"Could not checkpoint database: {e}")
                
                # Commit any pending transactions
                try:
                    self.persistence.conn.commit()
                except Exception:
                    pass
                
                # Close the connection to ensure all data is flushed
                self.persistence.conn.close()
                self.persistence.conn = None
            
            # Copy the database file to the target location
            db_path = Path(self.persistence.db_path)
            target_path = Path(file_path)
            
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the database file
            if db_path.exists():
                shutil.copy2(db_path, target_path)
                
                # Also copy WAL file if it exists (for complete backup)
                wal_path = db_path.with_suffix('.duckdb.wal')
                if wal_path.exists():
                    target_wal_path = target_path.with_suffix('.duckdb.wal')
                    shutil.copy2(wal_path, target_wal_path)
                
                logger.info(f"Project saved successfully to {file_path}")
                await self.controller.push_agui_log(f"Project saved successfully to {file_path}", "success")
            else:
                await self.controller.push_agui_log("No database file found to save.", "warning")
            
            # Reconnect to the database
            import duckdb
            self.persistence.conn = duckdb.connect(self.persistence.db_path)
                
        except Exception as e:
            logger.error(f"Error saving project: {e}")
            await self.controller.push_agui_log(f"Error saving project: {str(e)}", "error")
            # Try to reconnect on error
            try:
                import duckdb
                self.persistence.conn = duckdb.connect(self.persistence.db_path)
            except Exception:
                pass

    async def open_project(self, file_path: str) -> None:
        """Open a project database file and restore the session.
        
        SAFE APPROACH: Connects to the selected file without overwriting main database.
        """
        logger.info(f"📂 Opening project from {file_path}...")
        await self.controller.push_agui_log(f"Opening project from {file_path}...", "info")
        
        try:
            source_path = Path(file_path).resolve()
            if not source_path.exists():
                await self.controller.push_agui_log(f"Project file not found: {file_path}", "error")
                return
            
            # Check if the source path is the same as the current database path
            db_path = Path(self.persistence.db_path).resolve()
            if source_path == db_path:
                # Same file, just restore the session
                logger.info("Opening current database, restoring session...")
                await self.controller.push_agui_log("Opening current database, restoring session...", "info")
                await self.restore_session()
                return
            
            # SAFE APPROACH: Connect to the external file temporarily without overwriting main database
            # Close the current database connection
            if self.persistence.conn:
                self.persistence.conn.close()
            
            # Connect directly to the selected file (DO NOT COPY/OVERWRITE)
            import duckdb
            self.persistence.conn = duckdb.connect(str(source_path))
            # Update the db_path reference to track what file we're currently connected to
            self.persistence.db_path = str(source_path)
            
            # Ensure the opened database has proper schema (tables may not exist)
            self.persistence._create_schema()
            
            logger.info(f"Project opened successfully from {file_path}")
            await self.controller.push_agui_log(f"Project opened successfully. Restoring session...", "success")
            
            # Restore the session from the new database
            await self.restore_session()
            
        except Exception as e:
            logger.error(f"Error opening project: {e}")
            await self.controller.push_agui_log(f"Error opening project: {str(e)}", "error")
            # Try to reconnect on error
            try:
                import duckdb
                self.persistence.conn = duckdb.connect(self.persistence.db_path)
            except Exception:
                pass