"""
Action Execution System.

Executes advisor-suggested actions (LINK_ENTITIES, MERGE_ENTITIES, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState

logger = get_logger("core.actions")


class ActionExecutor:
    """Executes structured actions suggested by advisors."""
    
    # Action type constants
    LINK_ENTITIES = "LINK_ENTITIES"
    MERGE_ENTITIES = "MERGE_ENTITIES"
    CREATE_ENTITY = "CREATE_ENTITY"
    UPDATE_ENTITY = "UPDATE_ENTITY"
    DELETE_ENTITY = "DELETE_ENTITY"
    CREATE_RELATIONSHIP = "CREATE_RELATIONSHIP"
    DELETE_RELATIONSHIP = "DELETE_RELATIONSHIP"
    
    def __init__(self, forge_state: "ForgeState"):
        """Initialize action executor.
        
        Args:
            forge_state: ForgeState instance
        """
        self.forge_state = forge_state
        logger.info("ActionExecutor initialized")
    
    def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute an action.
        
        Args:
            action: Action type (e.g., "LINK_ENTITIES")
            payload: Action payload dictionary
            
        Returns:
            Dictionary with "success" bool and optional "error" message
        """
        try:
            logger.info(f"Executing action: {action} with payload: {payload}")
            
            if action == self.LINK_ENTITIES:
                return self._link_entities(payload)
            elif action == self.MERGE_ENTITIES:
                return self._merge_entities(payload)
            elif action == self.CREATE_ENTITY:
                return self._create_entity(payload)
            elif action == self.UPDATE_ENTITY:
                return self._update_entity(payload)
            elif action == self.DELETE_ENTITY:
                return self._delete_entity(payload)
            elif action == self.CREATE_RELATIONSHIP:
                return self._create_relationship(payload)
            elif action == self.DELETE_RELATIONSHIP:
                return self._delete_relationship(payload)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action}",
                }
                
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
    
    def _link_entities(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Link two entities with a relationship.
        
        Args:
            payload: {"source": "entity_id", "target": "entity_id", "type": "relationship_type", ...}
            
        Returns:
            Execution result
        """
        try:
            source_id = payload.get("source")
            target_id = payload.get("target")
            rel_type = payload.get("type", "associate")
            
            if not source_id or not target_id:
                return {"success": False, "error": "Missing source or target entity ID"}
            
            # Get entities
            source = self.forge_state.db.get_entity(source_id)
            target = self.forge_state.db.get_entity(target_id)
            
            if not source or not target:
                return {"success": False, "error": "Source or target entity not found"}
            
            # Create relationship
            from forge.core.models.relationship import create_relationship, RelationshipType
            
            relationship = create_relationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=RelationshipType(rel_type),
                label=payload.get("label", ""),
                strength=payload.get("strength", 0.5),
            )
            
            self.forge_state.db.save_relationship(relationship)
            
            logger.info(f"Linked entities: {source_id} -> {target_id}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to link entities: {e}")
            return {"success": False, "error": str(e)}
    
    def _merge_entities(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Merge two entities.
        
        Args:
            payload: {"source": "entity_id", "target": "entity_id"}
            
        Returns:
            Execution result
        """
        try:
            source_id = payload.get("source")
            target_id = payload.get("target")
            
            if not source_id or not target_id:
                return {"success": False, "error": "Missing source or target entity ID"}
            
            # Use Sentinel merge functionality if available
            from forge.phases.p0_extraction.sentinel import Sentinel
            
            sentinel = Sentinel(self.forge_state.db, self.forge_state.memory)
            # Note: Sentinel.accept_merge expects a candidate ID, not entity IDs
            # This is a simplified version
            # In practice, you'd need to create a merge candidate first
            
            logger.warning("Merge entities action needs full Sentinel integration")
            return {"success": False, "error": "Merge functionality needs Sentinel integration"}
            
        except Exception as e:
            logger.error(f"Failed to merge entities: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_entity(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new entity.
        
        Args:
            payload: {"name": "Entity Name", "entity_type": "ACTOR", "description": "...", ...}
            
        Returns:
            Execution result
        """
        try:
            from forge.core.models.entity import create_entity, EntityType
            
            entity = create_entity(
                entity_type=EntityType(payload.get("entity_type", "ACTOR")),
                name=payload.get("name", "Unnamed Entity"),
                description=payload.get("description", ""),
                tags=payload.get("tags", []),
                aliases=payload.get("aliases", []),
                attributes=payload.get("attributes", {}),
            )
            
            self.forge_state.db.save_entity(entity)
            
            logger.info(f"Created entity: {entity.id}")
            return {"success": True, "entity_id": entity.id}
            
        except Exception as e:
            logger.error(f"Failed to create entity: {e}")
            return {"success": False, "error": str(e)}
    
    def _update_entity(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update an existing entity.
        
        Args:
            payload: {"entity_id": "id", "name": "...", "description": "...", ...}
            
        Returns:
            Execution result
        """
        try:
            entity_id = payload.get("entity_id")
            if not entity_id:
                return {"success": False, "error": "Missing entity_id"}
            
            entity = self.forge_state.db.get_entity(entity_id)
            if not entity:
                return {"success": False, "error": "Entity not found"}
            
            # Update fields
            if "name" in payload:
                entity.name = payload["name"]
            if "description" in payload:
                entity.description = payload["description"]
            if "tags" in payload:
                entity.tags = payload["tags"]
            if "aliases" in payload:
                entity.aliases = payload["aliases"]
            if "attributes" in payload:
                entity.attributes = payload["attributes"]
            
            self.forge_state.db.save_entity(entity)
            
            logger.info(f"Updated entity: {entity_id}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to update entity: {e}")
            return {"success": False, "error": str(e)}
    
    def _delete_entity(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Delete an entity.
        
        Args:
            payload: {"entity_id": "id"}
            
        Returns:
            Execution result
        """
        try:
            entity_id = payload.get("entity_id")
            if not entity_id:
                return {"success": False, "error": "Missing entity_id"}
            
            # TODO: Implement entity deletion
            logger.warning("Delete entity action not yet implemented")
            return {"success": False, "error": "Delete entity not yet implemented"}
            
        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_relationship(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a relationship (same as link_entities but different interface).
        
        Args:
            payload: Relationship data
            
        Returns:
            Execution result
        """
        return self._link_entities(payload)
    
    def _delete_relationship(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Delete a relationship.
        
        Args:
            payload: {"relationship_id": "id"}
            
        Returns:
            Execution result
        """
        try:
            relationship_id = payload.get("relationship_id")
            if not relationship_id:
                return {"success": False, "error": "Missing relationship_id"}
            
            # TODO: Implement relationship deletion
            logger.warning("Delete relationship action not yet implemented")
            return {"success": False, "error": "Delete relationship not yet implemented"}
            
        except Exception as e:
            logger.error(f"Failed to delete relationship: {e}")
            return {"success": False, "error": str(e)}
