"""
EmbeddingService for PyScrAI Forge.

Provides CUDA-accelerated text embedding using sentence-transformers.
Uses two specialized models:
- BAAI/bge-base-en-v1.5: General purpose, optimal for entities/short relationships
- nomic-ai/nomic-embed-text-v1.5: Long context (8192 tokens), for documents/narratives
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating semantic embeddings from text."""
    
    def __init__(
        self,
        event_bus: EventBus,
        device: str = "cuda",
        general_model: str = "BAAI/bge-base-en-v1.5",
        long_context_model: str = "nomic-ai/nomic-embed-text-v1.5",
        batch_size: int = 32,
        long_context_threshold: int = 512,
    ):
        """Initialize the embedding service.
        
        Args:
            event_bus: Event bus for subscribing to events
            device: Device to use for inference ('cuda' or 'cpu')
            general_model: Model for general purpose embeddings
            long_context_model: Model for long context embeddings
            batch_size: Batch size for processing
            long_context_threshold: Token threshold for switching to long context model
        """
        self.event_bus = event_bus
        self.device = device
        self.general_model_name = general_model
        self.long_context_model_name = long_context_model
        self.batch_size = batch_size
        self.long_context_threshold = long_context_threshold
        
        # Models will be lazy-loaded
        self._general_model = None
        self._long_context_model = None
        
        # Cache for embeddings to avoid re-computation
        self._embedding_cache: Dict[str, List[float]] = {}
        
        # Batch queue for efficient processing
        self._entity_batch: List[Dict[str, Any]] = []
        self._relationship_batch: List[Dict[str, Any]] = []
        # Lazy initialization to avoid event loop binding issues
        self._batch_lock: Optional[asyncio.Lock] = None
        self._loop_id: Optional[int] = None
    
    def _ensure_batch_lock(self) -> asyncio.Lock:
        """Get or create batch lock for current event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
            
            # If we have a lock but it's for a different loop, recreate it
            if self._loop_id is not None and self._loop_id != loop_id:
                self._batch_lock = None
            
            # Create lock if needed
            if self._batch_lock is None:
                self._batch_lock = asyncio.Lock()
                self._loop_id = loop_id
        except RuntimeError:
            # No running event loop - create lock anyway (will be bound when used)
            if self._batch_lock is None:
                self._batch_lock = asyncio.Lock()
        
        return self._batch_lock
        
    @property
    def general_model(self):
        """Lazy-load general purpose model."""
        if self._general_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading general model {self.general_model_name} on {self.device}")
                self._general_model = SentenceTransformer(
                    self.general_model_name,
                    device=self.device
                )
                logger.info("General model loaded successfully")
            except ImportError:
                logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
                raise
            except Exception as e:
                logger.error(f"Failed to load general model: {e}")
                raise
        return self._general_model
    
    @property
    def long_context_model(self):
        """Lazy-load long context model."""
        if self._long_context_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading long context model {self.long_context_model_name} on {self.device}")
                self._long_context_model = SentenceTransformer(
                    self.long_context_model_name,
                    device=self.device
                )
                logger.info("Long context model loaded successfully")
            except ImportError:
                logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
                raise
            except Exception as e:
                logger.error(f"Failed to load long context model: {e}")
                raise
        return self._long_context_model
    
    async def start(self):
        """Start the service and subscribe to events."""
        logger.info("Starting EmbeddingService")
        await self.event_bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, self.handle_entity_extracted)
        await self.event_bus.subscribe(events.TOPIC_RELATIONSHIP_FOUND, self.handle_relationship_found)
        logger.info("EmbeddingService started")
    
    async def embed_text(
        self,
        text: str,
        use_long_context: bool = False
    ) -> List[float]:
        """Embed a single text string.
        
        Args:
            text: Text to embed
            use_long_context: Force use of long context model
            
        Returns:
            List of floats representing the embedding
        """
        # Check cache first
        cache_key = f"{text}:{use_long_context}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        # Auto-detect if we need long context model
        if not use_long_context and len(text.split()) > self.long_context_threshold:
            use_long_context = True
        
        # Select model
        model = self.long_context_model if use_long_context else self.general_model
        
        # Run embedding in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: model.encode(text, convert_to_tensor=False).tolist()
        )
        
        # Cache the result
        self._embedding_cache[cache_key] = embedding
        
        return embedding
    
    async def embed_batch(
        self,
        texts: List[str],
        use_long_context: bool = False
    ) -> List[List[float]]:
        """Embed a batch of texts efficiently.
        
        Args:
            texts: List of texts to embed
            use_long_context: Force use of long context model
            
        Returns:
            List of embeddings
        """
        if not texts:
            return []
        
        # Auto-detect if we need long context model
        if not use_long_context:
            avg_length = sum(len(t.split()) for t in texts) / len(texts)
            if avg_length > self.long_context_threshold:
                use_long_context = True
        
        # Select model
        model = self.long_context_model if use_long_context else self.general_model
        
        # Run batch embedding in thread pool
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(
                texts,
                batch_size=self.batch_size,
                convert_to_tensor=False
            ).tolist()
        )
        
        # Cache results
        for text, embedding in zip(texts, embeddings):
            cache_key = f"{text}:{use_long_context}"
            self._embedding_cache[cache_key] = embedding
        
        return embeddings
    
    async def handle_entity_extracted(self, payload: EventPayload):
        """Handle entity extraction events.
        
        Batches entities for efficient processing.
        """
        doc_id = payload.get("doc_id", "unknown")
        entities = payload.get("entities", [])
        
        logger.info(f"Embedding {len(entities)} entities from doc {doc_id}")
        
        # Prepare texts for embedding
        texts = []
        entity_data = []
        
        for entity in entities:
            # Create a text representation of the entity
            text = f"{entity.get('text', '')} ({entity.get('type', 'UNKNOWN')})"
            texts.append(text)
            entity_data.append({
                "doc_id": doc_id,
                "entity": entity,
                "text": text
            })
        
        # Batch embed
        embeddings = await self.embed_batch(texts, use_long_context=False)
        
        # Emit events for each embedded entity
        for data, embedding in zip(entity_data, embeddings):
            await self.event_bus.publish(
                events.TOPIC_ENTITY_EMBEDDED,
                {
                    "doc_id": data["doc_id"],
                    "entity": data["entity"],
                    "text": data["text"],
                    "embedding": embedding,
                    "dimension": len(embedding),
                }
            )
        
        logger.info(f"Successfully embedded {len(entities)} entities")
    
    async def handle_relationship_found(self, payload: EventPayload):
        """Handle relationship found events.
        
        Batches relationships for efficient processing.
        """
        doc_id = payload.get("doc_id", "unknown")
        relationships = payload.get("relationships", [])
        
        logger.info(f"Embedding {len(relationships)} relationships from doc {doc_id}")
        
        # Prepare texts for embedding
        texts = []
        relationship_data = []
        
        for rel in relationships:
            # Create a text representation of the relationship
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "RELATED_TO")
            text = f"{source} {rel_type} {target}"
            texts.append(text)
            relationship_data.append({
                "doc_id": doc_id,
                "relationship": rel,
                "text": text
            })
        
        # Batch embed
        embeddings = await self.embed_batch(texts, use_long_context=False)
        
        # Emit events for each embedded relationship
        for data, embedding in zip(relationship_data, embeddings):
            await self.event_bus.publish(
                events.TOPIC_RELATIONSHIP_EMBEDDED,
                {
                    "doc_id": data["doc_id"],
                    "relationship": data["relationship"],
                    "text": data["text"],
                    "embedding": embedding,
                    "dimension": len(embedding),
                }
            )
        
        logger.info(f"Successfully embedded {len(relationships)} relationships")
