"""
Entity Manager for Anvil Phase.

Provides CRUD operations and search for entities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator
from datetime import UTC, datetime

from forge.core.models.entity import Entity, EntityType
from forge.core.events.mutations import (
    create_entity_created_event,
    create_entity_updated_event,
    create_entity_deleted_event,
)
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState

logger = get_logger("anvil.manager")


class EntityManager:
    """Manages entity CRUD operations with event tracking.
    
    Usage:
        manager = EntityManager(state)
        
        # Get all actors
        actors = manager.get_by_type(EntityType.ACTOR)
        
        # Search entities
        results = manager.search("John")
        
        # Update entity
        entity.description = "Updated description"
        manager.update(entity)
    """
    
    def __init__(self, state: "ForgeState"):
        """Initialize the entity manager.
        
        Args:
            state: Application state
        """
        self.state = state
        self._events: list = []
    
    # ========== Read Operations ==========
    
    def get(self, entity_id: str) -> Entity | None:
        """Get an entity by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Entity if found, None otherwise
        """
        return self.state.db.get_entity(entity_id)
    
    def get_all(self) -> list[Entity]:
        """Get all entities.
        
        Returns:
            List of all entities
        """
        return self.state.db.get_all_entities()
    
    def get_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get entities of a specific type.
        
        Args:
            entity_type: Type to filter by
            
        Returns:
            List of matching entities
        """
        return self.state.db.get_entities_by_type(entity_type)
    
    def search(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        limit: int = 50,
    ) -> list[Entity]:
        """Search entities by name, aliases, or description.
        
        Args:
            query: Search query
            entity_types: Optional type filter
            limit: Maximum results
            
        Returns:
            Matching entities
        """
        query_lower = query.lower()
        results = []
        
        for entity in self.get_all():
            if entity_types and entity.type not in entity_types:
                continue
            
            # Check name
            if query_lower in entity.name.lower():
                results.append(entity)
                continue
            
            # Check aliases
            if any(query_lower in alias.lower() for alias in entity.aliases):
                results.append(entity)
                continue
            
            # Check description
            if query_lower in entity.description.lower():
                results.append(entity)
                continue
            
            if len(results) >= limit:
                break
        
        return results[:limit]
    
    def search_semantic(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[Entity, float]]:
        """Search entities using semantic similarity.
        
        Args:
            query: Search query
            top_k: Maximum results
            
        Returns:
            List of (entity, similarity_score) tuples
        """
        # Use vector memory for semantic search
        results = self.state.memory.search(query, top_k=top_k)
        
        entities_with_scores = []
        for entity_id, score in results:
            entity = self.get(entity_id)
            if entity:
                entities_with_scores.append((entity, score))
        
        return entities_with_scores
    
    def count(self, entity_type: EntityType | None = None) -> int:
        """Count entities.
        
        Args:
            entity_type: Optional type filter
            
        Returns:
            Count of entities
        """
        if entity_type:
            return len(self.get_by_type(entity_type))
        return len(self.get_all())
    
    def iterate(
        self,
        entity_type: EntityType | None = None,
    ) -> Iterator[Entity]:
        """Iterate over entities.
        
        Args:
            entity_type: Optional type filter
            
        Yields:
            Entity objects
        """
        if entity_type:
            yield from self.get_by_type(entity_type)
        else:
            yield from self.get_all()
    
    # ========== Write Operations ==========
    
    def create(self, entity: Entity) -> Entity:
        """Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity
        """
        self.state.db.save_entity(entity)
        
        # Add to vector memory
        self.state.memory.add_entity(entity)
        
        # Log event
        event = create_entity_created_event(
            entity_id=entity.id,
            entity_type=entity.entity_type.value,
            name=entity.name,
        )
        self._events.append(event)
        self.state.db.log_event(event)
        
        self.state.mark_dirty()
        logger.info(f"Created entity: {entity.name} ({entity.id})")
        
        return entity
    
    def update(self, entity: Entity) -> Entity:
        """Update an existing entity.
        
        Args:
            entity: Entity with updated values
            
        Returns:
            Updated entity
        """
        entity.updated_at = datetime.now(UTC)
        self.state.db.save_entity(entity)
        
        # Update vector memory
        self.state.memory.update_entity(entity)
        
        # Log event
        event = create_entity_updated_event(
            entity_id=entity.id,
            changes={"name": entity.name},
        )
        self._events.append(event)
        self.state.db.log_event(event)
        
        self.state.mark_dirty()
        logger.info(f"Updated entity: {entity.name} ({entity.id})")
        
        return entity
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: ID of entity to delete
            
        Returns:
            True if deleted, False if not found
        """
        entity = self.get(entity_id)
        if not entity:
            return False
        
        # Delete from database
        self.state.db.delete_entity(entity_id)
        
        # Remove from vector memory
        self.state.memory.remove_entity(entity_id)
        
        # Log event
        event = create_entity_deleted_event(
            entity_id=entity_id,
            name=entity.name,
        )
        self._events.append(event)
        self.state.db.log_event(event)
        
        self.state.mark_dirty()
        logger.info(f"Deleted entity: {entity.name} ({entity_id})")
        
        return True
    
    # ========== Batch Operations ==========
    
    def create_many(self, entities: list[Entity]) -> list[Entity]:
        """Create multiple entities.
        
        Args:
            entities: List of entities to create
            
        Returns:
            List of created entities
        """
        created = []
        for entity in entities:
            created.append(self.create(entity))
        return created
    
    def update_many(self, entities: list[Entity]) -> list[Entity]:
        """Update multiple entities.
        
        Args:
            entities: List of entities to update
            
        Returns:
            List of updated entities
        """
        updated = []
        for entity in entities:
            updated.append(self.update(entity))
        return updated
    
    def delete_many(self, entity_ids: list[str]) -> int:
        """Delete multiple entities.
        
        Args:
            entity_ids: List of entity IDs to delete
            
        Returns:
            Number of entities deleted
        """
        count = 0
        for entity_id in entity_ids:
            if self.delete(entity_id):
                count += 1
        return count
    
    # ========== Events ==========
    
    def get_events(self) -> list:
        """Get events from this session."""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear session events."""
        self._events.clear()
