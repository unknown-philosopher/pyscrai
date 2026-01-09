"""
Memory System - Vector DB integration with sqlite-vec.

Provides local-first semantic memory directly in world.db.
"""

from forge.systems.memory.vector_memory import (
    VectorMemory,
    VectorSearchResult,
    serialize_float32,
    deserialize_float32,
)
from forge.systems.memory.embeddings import (
    EmbeddingModel,
    get_embedding_model,
    encode_text,
    compute_similarity,
)

__all__ = [
    # Vector Memory
    "VectorMemory",
    "VectorSearchResult",
    "serialize_float32",
    "deserialize_float32",
    # Embeddings
    "EmbeddingModel",
    "get_embedding_model",
    "encode_text",
    "compute_similarity",
]
