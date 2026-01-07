"""Memory Service - Semantic search with sqlite-vec and FTS5 fallback.

This module provides a unified interface for semantic similarity search
using sentence-transformers embeddings. It supports:
- sqlite-vec for fast vector similarity (if available)
- FTS5 keyword search as fallback
- Simple keyword matching as ultimate fallback

Usage:
    service = MemoryService.create(db_path)
    service.add("entity_001", "John Smith is a spy working for MI6")
    results = service.search("British intelligence agent", limit=5)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result from the memory service."""
    entity_id: str
    text: str
    score: float  # 0.0 to 1.0, higher is more similar
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VectorInterface(Protocol):
    """Protocol for vector search implementations."""
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search for similar items."""
        ...
    
    def add(self, entity_id: str, text: str, metadata: Optional[dict] = None) -> None:
        """Add an item to the index."""
        ...
    
    def remove(self, entity_id: str) -> None:
        """Remove an item from the index."""
        ...
    
    def clear(self) -> None:
        """Clear all items."""
        ...
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        ...


class EmbeddingModel:
    """Wrapper for sentence-transformers embedding model."""
    
    _instance: Optional["EmbeddingModel"] = None
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding model.
        
        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self._model = None
        self._available = None
    
    @classmethod
    def get_instance(cls, model_name: str = "all-MiniLM-L6-v2") -> "EmbeddingModel":
        """Get singleton instance."""
        if cls._instance is None or cls._instance.model_name != model_name:
            cls._instance = cls(model_name)
        return cls._instance
    
    @property
    def available(self) -> bool:
        """Check if sentence-transformers is available."""
        if self._available is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._available = True
            except ImportError:
                self._available = False
                logger.warning("sentence-transformers not available, using keyword fallback")
        return self._available
    
    @property
    def model(self):
        """Lazy-load the model."""
        if self._model is None and self.available:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        return self._model
    
    def encode(self, text: str) -> Optional[List[float]]:
        """Encode text to embedding vector."""
        if not self.available or self.model is None:
            return None
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def encode_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Encode multiple texts to embeddings."""
        if not self.available or self.model is None:
            return None
        
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self.model_name == "all-MiniLM-L6-v2":
            return 384
        # Default for most models
        return 384


class SqliteVecService:
    """Vector search using sqlite-vec extension."""
    
    def __init__(self, db_path: Path, embedding_model: EmbeddingModel):
        """Initialize sqlite-vec service.
        
        Args:
            db_path: Path to the database
            embedding_model: Embedding model to use
        """
        self.db_path = Path(db_path)
        self.embedding_model = embedding_model
        self._vec_available = None
        self._ensure_tables()
    
    @property
    def vec_available(self) -> bool:
        """Check if sqlite-vec extension is available."""
        if self._vec_available is None:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.enable_load_extension(True)
                conn.load_extension("vec0")
                conn.close()
                self._vec_available = True
            except Exception:
                self._vec_available = False
                logger.warning("sqlite-vec extension not available")
        return self._vec_available
    
    def _ensure_tables(self) -> None:
        """Ensure vector tables exist."""
        if not self.vec_available:
            return
        
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        conn.load_extension("vec0")
        cursor = conn.cursor()
        
        try:
            # Create virtual table for vector search
            dim = self.embedding_model.dimension
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors
                USING vec0(
                    entity_id TEXT PRIMARY KEY,
                    embedding FLOAT[{dim}]
                )
            """)
            
            # Create metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_metadata (
                    entity_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def add(self, entity_id: str, text: str, metadata: Optional[dict] = None) -> None:
        """Add an item to the vector index."""
        if not self.vec_available:
            return
        
        embedding = self.embedding_model.encode(text)
        if embedding is None:
            return
        
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        conn.load_extension("vec0")
        cursor = conn.cursor()
        
        try:
            # Insert or replace vector
            cursor.execute(
                "INSERT OR REPLACE INTO memory_vectors (entity_id, embedding) VALUES (?, ?)",
                (entity_id, json.dumps(embedding))
            )
            
            # Insert or replace metadata
            cursor.execute(
                "INSERT OR REPLACE INTO memory_metadata (entity_id, text, metadata) VALUES (?, ?, ?)",
                (entity_id, text, json.dumps(metadata or {}))
            )
            
            conn.commit()
        finally:
            conn.close()
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search for similar items."""
        if not self.vec_available:
            return []
        
        query_embedding = self.embedding_model.encode(query)
        if query_embedding is None:
            return []
        
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        conn.load_extension("vec0")
        cursor = conn.cursor()
        
        try:
            # Search using cosine distance
            cursor.execute("""
                SELECT v.entity_id, m.text, m.metadata, 
                       vec_distance_cosine(v.embedding, ?) as distance
                FROM memory_vectors v
                JOIN memory_metadata m ON v.entity_id = m.entity_id
                ORDER BY distance
                LIMIT ?
            """, (json.dumps(query_embedding), limit))
            
            results = []
            for row in cursor.fetchall():
                entity_id, text, metadata_str, distance = row
                # Convert cosine distance to similarity (1 - distance)
                similarity = 1.0 - distance
                results.append(SearchResult(
                    entity_id=entity_id,
                    text=text,
                    score=similarity,
                    metadata=json.loads(metadata_str) if metadata_str else {}
                ))
            
            return results
            
        finally:
            conn.close()
    
    def remove(self, entity_id: str) -> None:
        """Remove an item from the index."""
        if not self.vec_available:
            return
        
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        conn.load_extension("vec0")
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM memory_vectors WHERE entity_id = ?", (entity_id,))
            cursor.execute("DELETE FROM memory_metadata WHERE entity_id = ?", (entity_id,))
            conn.commit()
        finally:
            conn.close()
    
    def clear(self) -> None:
        """Clear all items."""
        if not self.vec_available:
            return
        
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        conn.load_extension("vec0")
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM memory_vectors")
            cursor.execute("DELETE FROM memory_metadata")
            conn.commit()
        finally:
            conn.close()
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        if not self.embedding_model.available:
            return 0.0
        
        embeddings = self.embedding_model.encode_batch([text1, text2])
        if embeddings is None or len(embeddings) < 2:
            return 0.0
        
        # Calculate cosine similarity
        import math
        
        vec1, vec2 = embeddings
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class FTS5Service:
    """Keyword search using SQLite FTS5."""
    
    def __init__(self, db_path: Path):
        """Initialize FTS5 service.
        
        Args:
            db_path: Path to the database
        """
        self.db_path = Path(db_path)
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """Ensure FTS5 tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                USING fts5(entity_id, text, metadata)
            """)
            conn.commit()
        except sqlite3.OperationalError:
            # FTS5 might not be available
            pass
        finally:
            conn.close()
    
    def add(self, entity_id: str, text: str, metadata: Optional[dict] = None) -> None:
        """Add an item to the FTS index."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Remove existing entry
            cursor.execute("DELETE FROM memory_fts WHERE entity_id = ?", (entity_id,))
            # Insert new entry
            cursor.execute(
                "INSERT INTO memory_fts (entity_id, text, metadata) VALUES (?, ?, ?)",
                (entity_id, text, json.dumps(metadata or {}))
            )
            conn.commit()
        except sqlite3.OperationalError:
            pass  # FTS5 not available
        finally:
            conn.close()
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search for items matching the query."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Use FTS5 MATCH with BM25 ranking
            cursor.execute("""
                SELECT entity_id, text, metadata, bm25(memory_fts) as rank
                FROM memory_fts
                WHERE memory_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = []
            for row in cursor.fetchall():
                entity_id, text, metadata_str, rank = row
                # Normalize BM25 score to 0-1 range (approximate)
                score = 1.0 / (1.0 + abs(rank))
                results.append(SearchResult(
                    entity_id=entity_id,
                    text=text,
                    score=score,
                    metadata=json.loads(metadata_str) if metadata_str else {}
                ))
            
            return results
            
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()
    
    def remove(self, entity_id: str) -> None:
        """Remove an item from the index."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM memory_fts WHERE entity_id = ?", (entity_id,))
            conn.commit()
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
    
    def clear(self) -> None:
        """Clear all items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM memory_fts")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple Jaccard similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class SimpleKeywordService:
    """Simple keyword matching fallback when other services unavailable."""
    
    def __init__(self):
        """Initialize the simple keyword service."""
        self.items: dict[str, Tuple[str, dict]] = {}
    
    def add(self, entity_id: str, text: str, metadata: Optional[dict] = None) -> None:
        """Add an item."""
        self.items[entity_id] = (text, metadata or {})
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using simple keyword matching."""
        query_words = set(query.lower().split())
        
        results = []
        for entity_id, (text, metadata) in self.items.items():
            text_words = set(text.lower().split())
            
            # Calculate overlap
            overlap = len(query_words & text_words)
            if overlap > 0:
                score = overlap / max(len(query_words), len(text_words))
                results.append(SearchResult(
                    entity_id=entity_id,
                    text=text,
                    score=score,
                    metadata=metadata
                ))
        
        # Sort by score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
    
    def remove(self, entity_id: str) -> None:
        """Remove an item."""
        self.items.pop(entity_id, None)
    
    def clear(self) -> None:
        """Clear all items."""
        self.items.clear()
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple Jaccard similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class MemoryService:
    """Unified memory service with automatic fallback.
    
    Tries services in order:
    1. sqlite-vec (if extension available)
    2. FTS5 (if available in SQLite)
    3. Simple keyword matching
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        embedding_model: Optional[str] = "all-MiniLM-L6-v2"
    ):
        """Initialize the memory service.
        
        Args:
            db_path: Path to the database (None for in-memory)
            embedding_model: Name of embedding model to use
        """
        self.db_path = Path(db_path) if db_path else None
        self.embedding = EmbeddingModel.get_instance(embedding_model) if embedding_model else None
        
        # Try to initialize services
        self._vec_service: Optional[SqliteVecService] = None
        self._fts_service: Optional[FTS5Service] = None
        self._keyword_service = SimpleKeywordService()
        
        self._init_services()
    
    def _init_services(self) -> None:
        """Initialize available services."""
        if self.db_path and self.embedding:
            try:
                self._vec_service = SqliteVecService(self.db_path, self.embedding)
                if self._vec_service.vec_available:
                    logger.info("Using sqlite-vec for semantic search")
                    return
            except Exception as e:
                logger.warning(f"Failed to initialize sqlite-vec: {e}")
        
        if self.db_path:
            try:
                self._fts_service = FTS5Service(self.db_path)
                logger.info("Using FTS5 for keyword search")
            except Exception as e:
                logger.warning(f"Failed to initialize FTS5: {e}")
        
        logger.info("Using simple keyword matching")
    
    @classmethod
    def create(
        cls,
        db_path: Optional[Path] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ) -> "MemoryService":
        """Create a memory service instance.
        
        Args:
            db_path: Path to the database
            embedding_model: Name of embedding model
            
        Returns:
            Configured MemoryService instance
        """
        return cls(db_path, embedding_model)
    
    @property
    def service_type(self) -> str:
        """Get the type of search service being used."""
        if self._vec_service and self._vec_service.vec_available:
            return "sqlite-vec"
        elif self._fts_service:
            return "fts5"
        else:
            return "keyword"
    
    def add(self, entity_id: str, text: str, metadata: Optional[dict] = None) -> None:
        """Add an item to all available indices."""
        if self._vec_service and self._vec_service.vec_available:
            self._vec_service.add(entity_id, text, metadata)
        
        if self._fts_service:
            self._fts_service.add(entity_id, text, metadata)
        
        self._keyword_service.add(entity_id, text, metadata)
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using the best available service."""
        # Try sqlite-vec first
        if self._vec_service and self._vec_service.vec_available:
            results = self._vec_service.search(query, limit)
            if results:
                return results
        
        # Try FTS5
        if self._fts_service:
            results = self._fts_service.search(query, limit)
            if results:
                return results
        
        # Fall back to keyword matching
        return self._keyword_service.search(query, limit)
    
    def remove(self, entity_id: str) -> None:
        """Remove an item from all indices."""
        if self._vec_service:
            self._vec_service.remove(entity_id)
        
        if self._fts_service:
            self._fts_service.remove(entity_id)
        
        self._keyword_service.remove(entity_id)
    
    def clear(self) -> None:
        """Clear all indices."""
        if self._vec_service:
            self._vec_service.clear()
        
        if self._fts_service:
            self._fts_service.clear()
        
        self._keyword_service.clear()
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        # Use embeddings if available
        if self._vec_service and self._vec_service.vec_available:
            return self._vec_service.calculate_similarity(text1, text2)
        
        # Fall back to Jaccard similarity
        return self._keyword_service.calculate_similarity(text1, text2)
    
    def index_entities(self, entities: list) -> int:
        """Index a list of entities.
        
        Args:
            entities: List of Entity objects
            
        Returns:
            Number of entities indexed
        """
        count = 0
        for entity in entities:
            entity_id = entity.id
            
            # Build text from entity
            parts = []
            if hasattr(entity, "descriptor"):
                desc = entity.descriptor
                if hasattr(desc, "name"):
                    parts.append(desc.name)
                if hasattr(desc, "description"):
                    parts.append(desc.description or "")
                if hasattr(desc, "aliases"):
                    parts.extend(desc.aliases or [])
            
            text = " ".join(parts)
            if text:
                self.add(entity_id, text)
                count += 1
        
        return count

