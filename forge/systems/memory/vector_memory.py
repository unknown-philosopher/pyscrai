"""
Vector Memory System for Forge 3.0.

Implements sqlite-vec integration for local vector similarity search
directly within world.db. No external vector database required.

Technical Implementation:
- Storage: world.db hosts a vec0 virtual table for embeddings
- Runtime: Loads sqlite-vec extension and provides vector operations
- Serialization: float32 arrays serialized to BLOBs for storage
"""

from __future__ import annotations

import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from forge.systems.memory.embeddings import EmbeddingModel, get_embedding_model


# ============================================================================
# Serialization Helpers
# ============================================================================


def serialize_float32(vector: np.ndarray | Sequence[float]) -> bytes:
    """Serialize a float32 vector to bytes for sqlite-vec storage.
    
    Args:
        vector: Numpy array or sequence of floats
        
    Returns:
        Bytes representing the vector as packed float32 values
    """
    if isinstance(vector, np.ndarray):
        return vector.astype(np.float32).tobytes()
    return struct.pack(f"{len(vector)}f", *vector)


def deserialize_float32(blob: bytes) -> np.ndarray:
    """Deserialize bytes back to a float32 numpy array.
    
    Args:
        blob: Bytes from sqlite-vec storage
        
    Returns:
        Numpy array of float32 values
    """
    return np.frombuffer(blob, dtype=np.float32)


# ============================================================================
# Search Result
# ============================================================================


@dataclass
class VectorSearchResult:
    """Result from a vector similarity search."""
    
    row_id: int
    entity_id: str
    distance: float
    similarity: float  # 1 - distance for cosine
    
    @property
    def score(self) -> float:
        """Alias for similarity."""
        return self.similarity


# ============================================================================
# Vector Memory Manager
# ============================================================================


class VectorMemory:
    """Manages vector embeddings within world.db using sqlite-vec.
    
    Provides methods for:
    - Indexing entities with their embeddings
    - Similarity search across the vector store
    - Near-duplicate detection for the Sentinel
    
    Usage:
        vm = VectorMemory(db_path)
        vm.initialize()
        
        # Index an entity
        row_id = vm.index_entity(entity_id, "John Smith is a diplomat...")
        
        # Search for similar entities
        results = vm.search_similar("diplomat politician", limit=5)
    """
    
    ENTITY_TABLE = "entity_embeddings"
    RELATIONSHIP_TABLE = "relationship_embeddings"
    
    def __init__(
        self,
        db_path: str | Path,
        embedding_model: EmbeddingModel | None = None,
        dimension: int = 384,
    ):
        """Initialize VectorMemory.
        
        Args:
            db_path: Path to the world.db SQLite database
            embedding_model: Optional custom embedding model
            dimension: Embedding dimension (default 384 for all-MiniLM-L6-v2)
        """
        self.db_path = Path(db_path)
        self._embedding_model = embedding_model
        self.dimension = dimension
        self._vec_loaded = False
    
    @property
    def embedding_model(self) -> EmbeddingModel:
        """Get or create the embedding model."""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
            self.dimension = self._embedding_model.dimension
        return self._embedding_model
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with sqlite-vec loaded."""
        conn = sqlite3.connect(self.db_path)
        
        # Try to load sqlite-vec extension
        if not self._vec_loaded:
            try:
                import sqlite_vec
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
                self._vec_loaded = True
            except ImportError:
                # sqlite-vec not available, will use fallback
                pass
            except Exception:
                # Extension loading failed, continue without it
                pass
        
        return conn
    
    def initialize(self) -> bool:
        """Initialize vector tables in the database.
        
        Creates the vec0 virtual tables for entity and relationship embeddings.
        
        Returns:
            True if sqlite-vec is available, False if using fallback
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self._vec_loaded:
            # Create vec0 virtual tables for sqlite-vec
            try:
                cursor.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS {self.ENTITY_TABLE}
                    USING vec0(
                        embedding float[{self.dimension}]
                    )
                """)
                
                cursor.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS {self.RELATIONSHIP_TABLE}
                    USING vec0(
                        embedding float[{self.dimension}]
                    )
                """)
                
                # Create mapping table to link vec0 rowids to entity IDs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embedding_entity_map (
                        rowid INTEGER PRIMARY KEY,
                        entity_id TEXT NOT NULL UNIQUE,
                        entity_type TEXT DEFAULT 'entity'
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embedding_relationship_map (
                        rowid INTEGER PRIMARY KEY,
                        relationship_id TEXT NOT NULL UNIQUE
                    )
                """)
                
                conn.commit()
                conn.close()
                return True
                
            except sqlite3.OperationalError:
                # vec0 not available, use fallback
                self._vec_loaded = False
        
        # Fallback: store embeddings as BLOBs in regular tables
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.ENTITY_TABLE}_fallback (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL UNIQUE,
                entity_type TEXT DEFAULT 'entity',
                embedding BLOB NOT NULL
            )
        """)
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.RELATIONSHIP_TABLE}_fallback (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                relationship_id TEXT NOT NULL UNIQUE,
                embedding BLOB NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        return False
    
    def index_entity(
        self,
        entity_id: str,
        text: str,
        entity_type: str = "entity",
    ) -> int:
        """Index an entity with its embedding.
        
        Args:
            entity_id: Unique entity identifier
            text: Text to generate embedding from
            entity_type: Type classification for filtering
            
        Returns:
            Row ID in the embedding table
        """
        embedding = self.embedding_model.encode_single(text)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if self._vec_loaded:
                # Insert into vec0 table
                cursor.execute(
                    f"INSERT INTO {self.ENTITY_TABLE}(embedding) VALUES (?)",
                    (serialize_float32(embedding),)
                )
                rowid = cursor.lastrowid
                
                # Map rowid to entity_id
                cursor.execute(
                    """INSERT OR REPLACE INTO embedding_entity_map
                       (rowid, entity_id, entity_type) VALUES (?, ?, ?)""",
                    (rowid, entity_id, entity_type)
                )
            else:
                # Fallback table
                cursor.execute(
                    f"""INSERT OR REPLACE INTO {self.ENTITY_TABLE}_fallback
                        (entity_id, entity_type, embedding) VALUES (?, ?, ?)""",
                    (entity_id, entity_type, serialize_float32(embedding))
                )
                rowid = cursor.lastrowid
            
            conn.commit()
            return rowid
            
        finally:
            conn.close()
    
    def index_relationship(
        self,
        relationship_id: str,
        text: str,
    ) -> int:
        """Index a relationship with its embedding.
        
        Args:
            relationship_id: Unique relationship identifier
            text: Text to generate embedding from
            
        Returns:
            Row ID in the embedding table
        """
        embedding = self.embedding_model.encode_single(text)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if self._vec_loaded:
                cursor.execute(
                    f"INSERT INTO {self.RELATIONSHIP_TABLE}(embedding) VALUES (?)",
                    (serialize_float32(embedding),)
                )
                rowid = cursor.lastrowid
                
                cursor.execute(
                    """INSERT OR REPLACE INTO embedding_relationship_map
                       (rowid, relationship_id) VALUES (?, ?)""",
                    (rowid, relationship_id)
                )
            else:
                cursor.execute(
                    f"""INSERT OR REPLACE INTO {self.RELATIONSHIP_TABLE}_fallback
                        (relationship_id, embedding) VALUES (?, ?)""",
                    (relationship_id, serialize_float32(embedding))
                )
                rowid = cursor.lastrowid
            
            conn.commit()
            return rowid
            
        finally:
            conn.close()
    
    def search_similar(
        self,
        query: str,
        limit: int = 10,
        entity_type: str | None = None,
        threshold: float = 0.0,
    ) -> list[VectorSearchResult]:
        """Search for entities similar to the query.
        
        Args:
            query: Text to search for
            limit: Maximum number of results
            entity_type: Optional filter by entity type
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            List of VectorSearchResult objects, sorted by similarity
        """
        query_embedding = self.embedding_model.encode_single(query)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            results = []
            
            if self._vec_loaded:
                # Use sqlite-vec for fast similarity search
                cursor.execute(
                    f"""SELECT rowid, distance
                        FROM {self.ENTITY_TABLE}
                        WHERE embedding MATCH ?
                        ORDER BY distance
                        LIMIT ?""",
                    (serialize_float32(query_embedding), limit * 2)
                )
                
                for rowid, distance in cursor.fetchall():
                    # Get entity_id from mapping
                    cursor.execute(
                        "SELECT entity_id, entity_type FROM embedding_entity_map WHERE rowid = ?",
                        (rowid,)
                    )
                    row = cursor.fetchone()
                    if row:
                        entity_id, etype = row
                        
                        # Apply entity_type filter
                        if entity_type and etype != entity_type:
                            continue
                        
                        similarity = 1.0 - distance  # Convert distance to similarity
                        
                        if similarity >= threshold:
                            results.append(VectorSearchResult(
                                row_id=rowid,
                                entity_id=entity_id,
                                distance=distance,
                                similarity=similarity,
                            ))
                        
                        if len(results) >= limit:
                            break
            
            else:
                # Fallback: brute-force search
                table = f"{self.ENTITY_TABLE}_fallback"
                
                if entity_type:
                    cursor.execute(
                        f"SELECT rowid, entity_id, embedding FROM {table} WHERE entity_type = ?",
                        (entity_type,)
                    )
                else:
                    cursor.execute(f"SELECT rowid, entity_id, embedding FROM {table}")
                
                candidates = []
                for rowid, entity_id, embedding_blob in cursor.fetchall():
                    embedding = deserialize_float32(embedding_blob)
                    
                    # Cosine similarity
                    dot = np.dot(query_embedding, embedding)
                    norm = np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                    similarity = float(dot / norm) if norm > 0 else 0.0
                    
                    if similarity >= threshold:
                        candidates.append(VectorSearchResult(
                            row_id=rowid,
                            entity_id=entity_id,
                            distance=1.0 - similarity,
                            similarity=similarity,
                        ))
                
                # Sort by similarity and limit
                candidates.sort(key=lambda x: x.similarity, reverse=True)
                results = candidates[:limit]
            
            return results
            
        finally:
            conn.close()
    
    def find_near_duplicates(
        self,
        text: str,
        threshold: float = 0.85,
    ) -> list[VectorSearchResult]:
        """Find potential duplicate entities based on text similarity.
        
        Used by the Sentinel during merge operations to detect duplicates.
        
        Args:
            text: Text to check for duplicates
            threshold: Minimum similarity to consider a duplicate
            
        Returns:
            List of potential duplicates above the threshold
        """
        return self.search_similar(query=text, limit=5, threshold=threshold)
    
    def compute_similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """Compute similarity between two text strings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity between 0 and 1
        """
        return self.embedding_model.similarity(text1, text2)
    
    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity's embedding from the vector store.
        
        Args:
            entity_id: Entity to remove
            
        Returns:
            True if removed, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if self._vec_loaded:
                # Get rowid from mapping
                cursor.execute(
                    "SELECT rowid FROM embedding_entity_map WHERE entity_id = ?",
                    (entity_id,)
                )
                row = cursor.fetchone()
                if row:
                    rowid = row[0]
                    cursor.execute(
                        f"DELETE FROM {self.ENTITY_TABLE} WHERE rowid = ?",
                        (rowid,)
                    )
                    cursor.execute(
                        "DELETE FROM embedding_entity_map WHERE entity_id = ?",
                        (entity_id,)
                    )
                    conn.commit()
                    return True
            else:
                cursor.execute(
                    f"DELETE FROM {self.ENTITY_TABLE}_fallback WHERE entity_id = ?",
                    (entity_id,)
                )
                if cursor.rowcount > 0:
                    conn.commit()
                    return True
            
            return False
            
        finally:
            conn.close()
    
    def get_embedding_count(self) -> int:
        """Get the total number of indexed entities."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if self._vec_loaded:
                cursor.execute(f"SELECT COUNT(*) FROM {self.ENTITY_TABLE}")
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {self.ENTITY_TABLE}_fallback")
            
            return cursor.fetchone()[0]
            
        finally:
            conn.close()
