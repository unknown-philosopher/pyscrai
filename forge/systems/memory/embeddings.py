"""
Embedding Model wrapper for Forge 3.0.

Provides a singleton interface to sentence-transformers for generating
text embeddings locally.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Singleton wrapper for sentence-transformers embedding model.
    
    Provides thread-safe access to embedding generation with lazy loading.
    Uses GPU if available, otherwise falls back to CPU.
    
    Default model: all-MiniLM-L6-v2 (384 dimensions, fast and efficient)
    """
    
    _instance: "EmbeddingModel | None" = None
    _lock = threading.Lock()
    
    def __new__(cls, model_name: str = "all-MiniLM-L6-v2") -> "EmbeddingModel":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if self._initialized:
            return
        
        self.model_name = model_name
        self._model: "SentenceTransformer | None" = None
        self._dimension: int | None = None
        self._initialized = True
    
    def _load_model(self) -> "SentenceTransformer":
        """Lazy load the model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                # Try GPU first, fallback to CPU
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
                
                self._model = SentenceTransformer(self.model_name, device=device)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install sentence-transformers"
                ) from e
        
        return self._model
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension or 384
    
    def encode(self, text: str | list[str]) -> np.ndarray:
        """Generate embeddings for text(s).
        
        Args:
            text: Single string or list of strings to embed
            
        Returns:
            Numpy array of shape (n, dimension) for list input
            or (dimension,) for single string input
        """
        model = self._load_model()
        
        if isinstance(text, str):
            return model.encode(text, convert_to_numpy=True)
        else:
            return model.encode(text, convert_to_numpy=True)
    
    def encode_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            1D numpy array of shape (dimension,)
        """
        return self.encode(text)
    
    def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        emb1 = self.encode_single(text1)
        emb2 = self.encode_single(text2)
        
        # Cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def batch_similarity(
        self, query: str, candidates: list[str]
    ) -> list[tuple[int, float]]:
        """Compute similarity between query and multiple candidates.
        
        Args:
            query: Query text
            candidates: List of candidate texts
            
        Returns:
            List of (index, similarity) tuples, sorted by similarity descending
        """
        if not candidates:
            return []
        
        query_emb = self.encode_single(query)
        candidate_embs = self.encode(candidates)
        
        # Compute all similarities at once
        dot_products = np.dot(candidate_embs, query_emb)
        norms = np.linalg.norm(candidate_embs, axis=1) * np.linalg.norm(query_emb)
        
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        similarities = dot_products / norms
        
        # Sort by similarity descending
        results = [(i, float(sim)) for i, sim in enumerate(similarities)]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results


# Global singleton access
_embedding_model: EmbeddingModel | None = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingModel:
    """Get the global embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel(model_name)
    return _embedding_model


def encode_text(text: str | list[str]) -> np.ndarray:
    """Convenience function to encode text using the global model."""
    return get_embedding_model().encode(text)


def compute_similarity(text1: str, text2: str) -> float:
    """Convenience function to compute text similarity."""
    return get_embedding_model().similarity(text1, text2)
