"""Semantic Clustering for Loom Phase.

This module provides semantic clustering of entities to reduce the computational
cost of relationship inference by grouping entities with similar contexts.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pyscrai_core import Entity
    from pyscrai_core.memory_service import MemoryService

logger = logging.getLogger(__name__)


class SemanticClusterer:
    """Clusters entities by semantic similarity to reduce relationship inference cost.
    
    Groups entities into clusters based on their semantic context (name, description,
    attributes). This allows relationship inference to only compare entities within
    the same cluster, reducing N² comparisons to K*(N/K)² where K is the number of clusters.
    """
    
    def __init__(self, memory_service: Optional["MemoryService"] = None):
        """Initialize the SemanticClusterer.
        
        Args:
            memory_service: MemoryService instance for embedding calculations
        """
        self.memory_service = memory_service
    
    def cluster_entities(
        self,
        entities: List["Entity"],
        n_clusters: Optional[int] = None,
        similarity_threshold: float = 0.7
    ) -> Dict[str, List["Entity"]]:
        """Cluster entities by semantic similarity.
        
        Args:
            entities: List of entities to cluster
            n_clusters: Number of clusters to create (auto-determined if None)
            similarity_threshold: Minimum similarity for entities in same cluster
            
        Returns:
            Dictionary mapping cluster_id to list of entities
        """
        if not entities:
            return {}
        
        if len(entities) <= 3:
            # Too few entities, return single cluster
            return {"cluster_0": entities}
        
        if not self.memory_service or not self.memory_service.embedding:
            logger.warning("MemoryService or embedding model not available, using single cluster")
            return {"cluster_0": entities}
        
        # Build context strings for all entities
        contexts = [self._build_context(e) for e in entities]
        
        # Embed all contexts
        embeddings = self.memory_service.embedding.encode_batch(contexts)
        if not embeddings or len(embeddings) != len(entities):
            logger.warning("Failed to generate embeddings, using single cluster")
            return {"cluster_0": entities}
        
        # Determine number of clusters
        if n_clusters is None:
            # Heuristic: sqrt of entity count, but at least 2 and at most 10
            n_clusters = max(2, min(10, int(math.sqrt(len(entities)))))
        
        # Cluster embeddings
        cluster_assignments = self._cluster_embeddings(
            embeddings,
            n_clusters=n_clusters,
            similarity_threshold=similarity_threshold
        )
        
        # Map entities to clusters
        result = {}
        for i, entity in enumerate(entities):
            cluster_id = f"cluster_{cluster_assignments[i]}"
            result.setdefault(cluster_id, []).append(entity)
        
        logger.info(f"Clustered {len(entities)} entities into {len(result)} clusters")
        return result
    
    def _build_context(self, entity: "Entity") -> str:
        """Build semantic context string for an entity.
        
        Args:
            entity: Entity to build context for
            
        Returns:
            Context string containing name, description, and key attributes
        """
        parts = []
        
        # Add descriptor information
        if hasattr(entity, "descriptor") and entity.descriptor:
            desc = entity.descriptor
            if hasattr(desc, "name") and desc.name:
                parts.append(desc.name)
            if hasattr(desc, "description") and desc.description:
                parts.append(desc.description)
            if hasattr(desc, "bio") and desc.bio:
                parts.append(desc.bio)
            if hasattr(desc, "aliases") and desc.aliases:
                parts.extend(desc.aliases)
        
        # Add state information (key attributes)
        if hasattr(entity, "state") and entity.state:
            if hasattr(entity.state, "resources") and entity.state.resources:
                # Add key attributes that help identify semantic domain
                for key, value in entity.state.resources.items():
                    if isinstance(value, str) and len(value) < 100:  # Skip very long values
                        parts.append(f"{key}: {value}")
        
        return " ".join(str(p) for p in parts if p)
    
    def _cluster_embeddings(
        self,
        embeddings: List[List[float]],
        n_clusters: int,
        similarity_threshold: float = 0.7
    ) -> List[int]:
        """Cluster embeddings using simple threshold-based approach.
        
        Uses a simple approach: start with first entity as cluster 0, then for each
        subsequent entity, assign to existing cluster if max similarity > threshold,
        otherwise create new cluster.
        
        Args:
            embeddings: List of embedding vectors
            n_clusters: Target number of clusters
            similarity_threshold: Minimum similarity for same cluster
            
        Returns:
            List of cluster assignments (one per entity)
        """
        if not embeddings:
            return []
        
        # Try to use sklearn KMeans if available
        try:
            from sklearn.cluster import KMeans
            import numpy as np
            
            # Convert to numpy array
            X = np.array(embeddings)
            
            # Normalize embeddings (L2 normalization)
            norms = np.linalg.norm(X, axis=1, keepdims=True)
            X_normalized = X / (norms + 1e-8)
            
            # Run KMeans
            kmeans = KMeans(n_clusters=min(n_clusters, len(embeddings)), random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(X_normalized)
            
            return cluster_labels.tolist()
            
        except ImportError:
            # Fallback to simple threshold-based clustering
            logger.info("sklearn not available, using threshold-based clustering")
            return self._threshold_cluster(embeddings, similarity_threshold)
    
    def _threshold_cluster(
        self,
        embeddings: List[List[float]],
        similarity_threshold: float
    ) -> List[int]:
        """Simple threshold-based clustering.
        
        Args:
            embeddings: List of embedding vectors
            similarity_threshold: Minimum similarity for same cluster
            
        Returns:
            List of cluster assignments
        """
        if not embeddings:
            return []
        
        cluster_assignments = [0]  # First entity in cluster 0
        cluster_centroids = [embeddings[0]]  # First embedding as centroid
        
        for i in range(1, len(embeddings)):
            emb = embeddings[i]
            
            # Find cluster with highest similarity
            max_similarity = -1
            best_cluster = 0
            
            for cluster_id, centroid in enumerate(cluster_centroids):
                similarity = self._cosine_similarity(emb, centroid)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_cluster = cluster_id
            
            # Assign to existing cluster if similarity is high enough
            if max_similarity >= similarity_threshold:
                cluster_assignments.append(best_cluster)
                # Update centroid (simple average)
                cluster_centroids[best_cluster] = [
                    (cluster_centroids[best_cluster][j] + emb[j]) / 2
                    for j in range(len(emb))
                ]
            else:
                # Create new cluster
                cluster_assignments.append(len(cluster_centroids))
                cluster_centroids.append(emb)
        
        return cluster_assignments
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_cluster_labels(self, clusters: Dict[str, List["Entity"]]) -> Dict[str, str]:
        """Generate human-readable labels for clusters.
        
        Args:
            clusters: Dictionary of cluster_id to entities
            
        Returns:
            Dictionary mapping cluster_id to label
        """
        labels = {}
        
        for cluster_id, entities in clusters.items():
            if not entities:
                labels[cluster_id] = "Empty"
                continue
            
            # Extract common terms from entity names/descriptions
            terms = []
            for entity in entities[:5]:  # Sample first 5 entities
                if hasattr(entity, "descriptor") and entity.descriptor:
                    if hasattr(entity.descriptor, "name") and entity.descriptor.name:
                        terms.append(entity.descriptor.name.split()[0])  # First word
            
            if terms:
                # Use most common term as label
                from collections import Counter
                most_common = Counter(terms).most_common(1)[0][0]
                labels[cluster_id] = most_common.title()
            else:
                labels[cluster_id] = cluster_id.replace("_", " ").title()
        
        return labels
