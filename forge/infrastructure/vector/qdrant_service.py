"""
QdrantService for PyScrAI Forge.

Provides GPU-accelerated vector storage and similarity search using Qdrant.
Manages two collections:
- entities: Entity embeddings with metadata
- relationships: Relationship embeddings with endpoint information
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any, Optional, NamedTuple
from dataclasses import dataclass

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events

logger = logging.getLogger(__name__)


@dataclass
class SimilarEntity:
    """Represents a similar entity from vector search."""
    entity_id: str
    score: float
    metadata: Dict[str, Any]


class QdrantService:
    """Service for vector storage and similarity search."""
    
    def __init__(
        self,
        event_bus: EventBus,
        url: str = ":memory:",
        api_key: Optional[str] = None,
        embedding_dimension: int = 768,
    ):
        """Initialize the Qdrant service.
        
        Args:
            event_bus: Event bus for subscribing to events
            url: Qdrant URL (':memory:' for in-memory, or 'http://localhost:6333')
            api_key: Optional API key for authentication
            embedding_dimension: Dimension of embeddings (768 for bge/nomic models)
        """
        self.event_bus = event_bus
        self.url = url
        self.api_key = api_key
        self.embedding_dimension = embedding_dimension
        
        # Client will be lazy-loaded
        self._client = None
        self._initialized = False
        
    @property
    def client(self):
        """Lazy-load Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                logger.info(f"Connecting to Qdrant at {self.url}")
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                )
                logger.info("Connected to Qdrant successfully")
            except ImportError:
                logger.error("qdrant-client not installed. Run: pip install qdrant-client")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {e}")
                raise
        return self._client
    
    async def start(self):
        """Start the service and subscribe to events."""
        logger.info("Starting QdrantService")
        
        # Initialize collections
        await self._initialize_collections()
        
        # Subscribe to embedding events
        await self.event_bus.subscribe(events.TOPIC_ENTITY_EMBEDDED, self.handle_entity_embedded)
        await self.event_bus.subscribe(events.TOPIC_RELATIONSHIP_EMBEDDED, self.handle_relationship_embedded)
        
        self._initialized = True
        logger.info("QdrantService started")
    
    async def _initialize_collections(self):
        """Initialize Qdrant collections for entities and relationships."""
        from qdrant_client.models import Distance, VectorParams
        
        loop = asyncio.get_event_loop()
        
        # Create entities collection
        try:
            await loop.run_in_executor(
                None,
                lambda: self.client.create_collection(
                    collection_name="entities",
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
            )
            logger.info("Created 'entities' collection")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("'entities' collection already exists")
            else:
                logger.error(f"Failed to create 'entities' collection: {e}")
                raise
        
        # Create relationships collection
        try:
            await loop.run_in_executor(
                None,
                lambda: self.client.create_collection(
                    collection_name="relationships",
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
            )
            logger.info("Created 'relationships' collection")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("'relationships' collection already exists")
            else:
                logger.error(f"Failed to create 'relationships' collection: {e}")
                raise
    
    async def add_entity_embedding(
        self,
        entity_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ):
        """Add an entity embedding to the vector store.
        
        Args:
            entity_id: Unique identifier for the entity
            embedding: Vector embedding
            metadata: Additional metadata (type, label, etc.)
        """
        from qdrant_client.models import PointStruct
        
        point = PointStruct(
            id=entity_id,
            vector=embedding,
            payload={
                "entity_id": entity_id,
                **metadata
            }
        )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.upsert(
                collection_name="entities",
                points=[point]
            )
        )
        
        logger.debug(f"Added entity embedding: {entity_id}")
    
    async def add_relationship_embedding(
        self,
        relationship_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ):
        """Add a relationship embedding to the vector store.
        
        Args:
            relationship_id: Unique identifier for the relationship
            embedding: Vector embedding
            metadata: Additional metadata (source, target, type, etc.)
        """
        from qdrant_client.models import PointStruct
        
        point = PointStruct(
            id=relationship_id,
            vector=embedding,
            payload={
                "relationship_id": relationship_id,
                **metadata
            }
        )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.upsert(
                collection_name="relationships",
                points=[point]
            )
        )
        
        logger.debug(f"Added relationship embedding: {relationship_id}")
    
    async def find_similar_entities(
        self,
        embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[SimilarEntity]:
        """Find similar entities based on embedding.
        
        Args:
            embedding: Query embedding
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of similar entities with scores
        """
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.client.query_points(
                collection_name="entities",
                query=embedding,
                limit=limit,
                score_threshold=score_threshold
            ).points
        )
        
        similar_entities = []
        for result in results:
            payload = result.payload or {}
            similar_entities.append(SimilarEntity(
                entity_id=payload.get("entity_id", str(result.id)),
                score=result.score,
                metadata=payload
            ))
        
        return similar_entities
    
    async def deduplicate_entities(
        self,
        similarity_threshold: float = 0.85
    ) -> List[tuple[str, str, float]]:
        """Find potential duplicate entities.
        
        Args:
            similarity_threshold: Minimum similarity to consider duplicates
            
        Returns:
            List of (entity1_id, entity2_id, similarity_score) tuples
        """
        # Get all entity points
        loop = asyncio.get_event_loop()
        
        # Scroll through all entities
        scroll_result = await loop.run_in_executor(
            None,
            lambda: self.client.scroll(
                collection_name="entities",
                limit=1000,  # Adjust based on expected entity count
                with_vectors=True
            )
        )
        
        points = scroll_result[0]
        duplicates = []
        
        # Check each entity against all others
        for i, point in enumerate(points):
            vector = point.vector
            # Handle different vector formats
            if isinstance(vector, dict):
                # Named vectors case
                continue
            elif isinstance(vector, list) and vector and isinstance(vector[0], list):
                # Multi-vector case - use first vector
                vector = vector[0]
            
            if not vector or not isinstance(vector, list):
                continue
            
            # Ensure we have a flat list of numbers
            try:
                # Cast to List[float] for type checker
                embedding: List[float] = [float(v) if not isinstance(v, list) else float(v[0]) for v in vector]
            except (TypeError, ValueError, IndexError):
                continue
                
            # Find similar entities
            similar = await self.find_similar_entities(
                embedding=embedding,
                limit=10,
                score_threshold=similarity_threshold
            )
            
            # Filter out self and create pairs
            payload = point.payload or {}
            entity_id = payload.get("entity_id", str(point.id))
            for sim in similar:
                if sim.entity_id != entity_id and sim.score >= similarity_threshold:
                    # Avoid duplicate pairs (A,B) and (B,A)
                    pair = tuple(sorted([entity_id, sim.entity_id]))
                    if pair not in [(d[0], d[1]) for d in duplicates]:
                        duplicates.append((pair[0], pair[1], sim.score))
        
        logger.info(f"Found {len(duplicates)} potential duplicate pairs")
        return duplicates
    
    async def handle_entity_embedded(self, payload: EventPayload):
        """Handle entity embedded events."""
        entity = payload.get("entity", {})
        embedding = payload.get("embedding", [])
        text = payload.get("text", "")
        doc_id = payload.get("doc_id", "unknown")
        
        # Create entity ID from text and type
        entity_type = entity.get("type", "UNKNOWN")
        entity_text = entity.get("text", text)
        entity_id = f"{entity_type}:{entity_text}"
        
        # Store in Qdrant
        await self.add_entity_embedding(
            entity_id=entity_id,
            embedding=embedding,
            metadata={
                "type": entity_type,
                "label": entity_text,
                "text": text,
                "doc_id": doc_id,
            }
        )
        
        logger.debug(f"Stored entity embedding: {entity_id}")
    
    async def handle_relationship_embedded(self, payload: EventPayload):
        """Handle relationship embedded events."""
        relationship = payload.get("relationship", {})
        embedding = payload.get("embedding", [])
        text = payload.get("text", "")
        doc_id = payload.get("doc_id", "unknown")
        
        # Create relationship ID
        source = relationship.get("source", "")
        target = relationship.get("target", "")
        rel_type = relationship.get("type", "RELATED_TO")
        relationship_id = f"{source}:{rel_type}:{target}"
        
        # Store in Qdrant
        await self.add_relationship_embedding(
            relationship_id=relationship_id,
            embedding=embedding,
            metadata={
                "source": source,
                "target": target,
                "type": rel_type,
                "text": text,
                "doc_id": doc_id,
            }
        )
        
        logger.debug(f"Stored relationship embedding: {relationship_id}")
