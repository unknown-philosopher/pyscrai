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
from uuid import UUID, uuid5, NAMESPACE_DNS

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
    
    @staticmethod
    def _string_to_uuid(string_id: str) -> UUID:
        """Convert a string ID to a UUID using deterministic hashing.
        
        Args:
            string_id: String identifier (e.g., "PERSON:Alice")
            
        Returns:
            UUID object
        """
        # Use uuid5 (SHA-1 based) for deterministic UUID generation
        # This ensures the same string always maps to the same UUID
        return uuid5(NAMESPACE_DNS, string_id)
        
    @property
    def client(self):
        """Lazy-load Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                logger.info(f"Connecting to Qdrant (in-memory mode: {self.url == ':memory:'})")
                
                # Use location=":memory:" parameter for in-memory mode
                if self.url == ":memory:":
                    self._client = QdrantClient(location=":memory:")
                else:
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
        
        # Convert string ID to UUID for Qdrant
        uuid_id = self._string_to_uuid(entity_id)
        
        point = PointStruct(
            id=uuid_id,
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
        
        # Convert string ID to UUID for Qdrant
        uuid_id = self._string_to_uuid(relationship_id)
        
        point = PointStruct(
            id=uuid_id,
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
        
        Uses a more efficient algorithm that:
        1. Only compares each pair once
        2. Uses a set for O(1) duplicate checking
        3. Limits comparisons to reduce false positives
        
        Args:
            similarity_threshold: Minimum similarity to consider duplicates
            
        Returns:
            List of (entity1_id, entity2_id, similarity_score) tuples
        """
        # Get all entity points with error handling
        loop = asyncio.get_event_loop()
        
        points = []
        try:
            # Use pagination to safely scroll through all entities
            # This avoids IndexError when collection state changes during scroll
            offset = None
            limit = 100  # Smaller batches to reduce risk of index mismatches
            
            while True:
                try:
                    # Capture offset in closure to avoid lambda closure issues
                    current_offset = offset
                    scroll_result = await loop.run_in_executor(
                        None,
                        lambda: self.client.scroll(
                            collection_name="entities",
                            limit=limit,
                            offset=current_offset,
                            with_vectors=True
                        )
                    )
                    
                    batch_points, next_offset = scroll_result
                    
                    if not batch_points:
                        break
                    
                    points.extend(batch_points)
                    
                    # Check if we've reached the end
                    if next_offset is None:
                        break
                    
                    offset = next_offset
                    
                except IndexError as e:
                    # Handle index out of bounds - collection may have changed
                    logger.warning(
                        f"IndexError during scroll (collection may have changed): {e}. "
                        f"Collected {len(points)} points so far. Continuing with available data."
                    )
                    break
                except Exception as e:
                    logger.error(f"Error scrolling entities: {e}")
                    # If we have some points, continue with what we have
                    if points:
                        logger.info(f"Continuing with {len(points)} points collected before error")
                        break
                    raise
                    
        except Exception as e:
            logger.error(f"Failed to retrieve entities for deduplication: {e}")
            return []
        
        if len(points) < 2:
            logger.info("Not enough entities for deduplication")
            return []
        
        # Use a set for O(1) duplicate pair checking
        seen_pairs: set[tuple[str, str]] = set()
        duplicates: list[tuple[str, str, float]] = []
        
        # Track entities we've already processed to avoid redundant comparisons
        processed_entities: set[str] = set()
        
        # Check each entity against others
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
            
            payload = point.payload or {}
            entity_id = payload.get("entity_id", str(point.id))
            entity_type = payload.get("type", "")
            
            # Skip if we've already processed this entity as a query
            if entity_id in processed_entities:
                continue
                
            # Find similar entities (limit to top 5 to reduce false positives)
            similar = await self.find_similar_entities(
                embedding=embedding,
                limit=5,  # Reduced from 10 to reduce false positives
                score_threshold=similarity_threshold
            )
            
            # Filter out self and create pairs
            for sim in similar:
                if sim.entity_id == entity_id:
                    continue
                    
                # Only consider pairs we haven't seen
                # Create sorted pair as 2-element tuple
                sorted_ids = sorted([entity_id, sim.entity_id])
                pair: tuple[str, str] = (sorted_ids[0], sorted_ids[1])
                if pair in seen_pairs:
                    continue
                
                # Additional filtering: only compare entities of the same type
                # (this reduces false positives significantly)
                sim_payload = sim.metadata or {}
                sim_type = sim_payload.get("type", "")
                if entity_type and sim_type and entity_type != sim_type:
                    continue
                
                # Only add if similarity is high enough
                if sim.score >= similarity_threshold:
                    duplicates.append((pair[0], pair[1], sim.score))
                    seen_pairs.add(pair)
            
            # Mark this entity as processed
            processed_entities.add(entity_id)
        
        logger.info(
            f"Found {len(duplicates)} potential duplicate pairs "
            f"(from {len(points)} entities, threshold={similarity_threshold})"
        )
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
    
    async def clear_collections(self) -> None:
        """Clear both entities and relationships collections by deleting and recreating them.
        
        This is useful when re-indexing data to avoid IndexError from stale collection state.
        """
        loop = asyncio.get_event_loop()
        
        # Delete entities collection
        try:
            await loop.run_in_executor(
                None,
                lambda: self.client.delete_collection(collection_name="entities")
            )
            logger.info("Deleted 'entities' collection")
        except Exception as e:
            if "doesn't exist" not in str(e).lower() and "not found" not in str(e).lower():
                logger.warning(f"Error deleting 'entities' collection: {e}")
        
        # Delete relationships collection
        try:
            await loop.run_in_executor(
                None,
                lambda: self.client.delete_collection(collection_name="relationships")
            )
            logger.info("Deleted 'relationships' collection")
        except Exception as e:
            if "doesn't exist" not in str(e).lower() and "not found" not in str(e).lower():
                logger.warning(f"Error deleting 'relationships' collection: {e}")
        
        # Recreate collections
        await self._initialize_collections()
        logger.info("Collections cleared and recreated")