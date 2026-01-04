"""Operation handlers for executing UserProxyAgent operations.

These handlers take the structured operations from UserProxyAgent and
actually modify the entities and relationships in the DataManager.
"""

import uuid
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship, RelationshipType


class OperationHandler:
    """Handles execution of operations from UserProxyAgent."""
    
    def __init__(self, entities: list["Entity"], relationships: list["Relationship"]):
        """
        Initialize operation handler.
        
        Args:
            entities: List of entities (will be modified in place)
            relationships: List of relationships (will be modified in place)
        """
        self.entities = entities
        self.relationships = relationships
    
    def execute_operation(self, operation_data: dict) -> tuple[str, bool]:
        """
        Execute an operation based on operation data from UserProxyAgent.
        
        Args:
            operation_data: Dictionary with 'operation', 'entities_involved', 'details', 'message'
            
        Returns:
            Tuple of (result_message, success)
        """
        operation = operation_data.get("operation", "")
        details = operation_data.get("details", {})
        
        try:
            if operation == "merge":
                return self._merge_entities(details)
            elif operation == "split":
                return self._split_entity(details)
            elif operation == "add_relationship":
                return self._add_relationship(details)
            elif operation == "remove_entity":
                return self._remove_entity(details)
            elif operation == "modify_entity":
                return self._modify_entity(details)
            elif operation == "list":
                return self._list_entities(details)
            elif operation == "help":
                return (operation_data.get("message", "Help message"), True)
            else:
                return (f"Unknown operation: {operation}", False)
        except Exception as e:
            return (f"Error executing operation: {str(e)}", False)
    
    def _merge_entities(self, details: dict) -> tuple[str, bool]:
        """Merge one entity into another.
        
        Args:
            details: Should contain 'keep_id' and 'merge_id'
        """
        keep_id = details.get("keep_id")
        merge_id = details.get("merge_id")
        
        if not keep_id or not merge_id:
            return ("Merge operation requires 'keep_id' and 'merge_id'", False)
        
        # Find entities
        keep_entity = next((e for e in self.entities if e.id == keep_id), None)
        merge_entity = next((e for e in self.entities if e.id == merge_id), None)
        
        if not keep_entity:
            return (f"Entity {keep_id} not found", False)
        if not merge_entity:
            return (f"Entity {merge_id} not found", False)
        
        # Merge descriptors (combine bio if present)
        if merge_entity.descriptor.bio:
            if keep_entity.descriptor.bio:
                keep_entity.descriptor.bio += "\n\n" + merge_entity.descriptor.bio
            else:
                keep_entity.descriptor.bio = merge_entity.descriptor.bio
        
        # Update all relationships pointing to merge_id to point to keep_id
        for rel in self.relationships:
            if rel.source_id == merge_id:
                rel.source_id = keep_id
            if rel.target_id == merge_id:
                rel.target_id = keep_id
        
        # Remove duplicate relationships (same source, target, type)
        seen = set()
        to_remove = []
        for rel in self.relationships:
            key = (rel.source_id, rel.target_id, rel.relationship_type.value)
            if key in seen:
                to_remove.append(rel)
            else:
                seen.add(key)
        
        for rel in to_remove:
            self.relationships.remove(rel)
        
        # Remove the merged entity
        self.entities.remove(merge_entity)
        
        keep_name = keep_entity.descriptor.name if keep_entity.descriptor else keep_id
        merge_name = merge_entity.descriptor.name if merge_entity.descriptor else merge_id
        
        return (f"Merged '{merge_name}' into '{keep_name}'", True)
    
    def _split_entity(self, details: dict) -> tuple[str, bool]:
        """Split an entity into multiple new entities.
        
        Args:
            details: Should contain 'entity_id' and 'split_into' (list of new entity names)
        """
        entity_id = details.get("entity_id")
        split_into = details.get("split_into", [])
        
        if not entity_id:
            return ("Split operation requires 'entity_id'", False)
        if not split_into or len(split_into) < 2:
            return ("Split operation requires at least 2 new entity names in 'split_into'", False)
        
        # Find entity
        entity = next((e for e in self.entities if e.id == entity_id), None)
        if not entity:
            return (f"Entity {entity_id} not found", False)
        
        # This is a complex operation - for now, return a message saying it's not fully implemented
        # A full implementation would need to ask the LLM which attributes go to which new entity
        entity_name = entity.descriptor.name if entity.descriptor else entity_id
        return (
            f"Split operation is not fully implemented yet. "
            f"To split '{entity_name}' into {split_into}, please delete the entity and create new ones manually.",
            False
        )
    
    def _add_relationship(self, details: dict) -> tuple[str, bool]:
        """Add a new relationship between entities.
        
        Args:
            details: Should contain 'source_id', 'target_id', and 'type'
        """
        from pyscrai_core import Relationship, RelationshipType
        
        source_id = details.get("source_id")
        target_id = details.get("target_id")
        rel_type_str = details.get("type", "custom")
        
        if not source_id or not target_id:
            return ("Add relationship requires 'source_id' and 'target_id'", False)
        
        # Find entities
        source_entity = next((e for e in self.entities if e.id == source_id), None)
        target_entity = next((e for e in self.entities if e.id == target_id), None)
        
        if not source_entity:
            return (f"Source entity {source_id} not found", False)
        if not target_entity:
            return (f"Target entity {target_id} not found", False)
        
        # Parse relationship type
        try:
            # Handle common variations
            rel_type_map = {
                "supports": RelationshipType.ALLIANCE,
                "conflicts": RelationshipType.ENMITY,
                "related_to": RelationshipType.CUSTOM,
            }
            if rel_type_str.lower() in rel_type_map:
                rel_type = rel_type_map[rel_type_str.lower()]
            else:
                # Try to match enum value
                rel_type = RelationshipType(rel_type_str.lower())
        except (ValueError, KeyError):
            rel_type = RelationshipType.CUSTOM
        
        # Check if relationship already exists
        existing = next(
            (
                r for r in self.relationships
                if r.source_id == source_id
                and r.target_id == target_id
                and r.relationship_type == rel_type
            ),
            None
        )
        if existing:
            return ("Relationship already exists", False)
        
        # Create new relationship
        new_rel = Relationship(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            description=details.get("description", "")
        )
        self.relationships.append(new_rel)
        
        source_name = source_entity.descriptor.name if source_entity.descriptor else source_id
        target_name = target_entity.descriptor.name if target_entity.descriptor else target_id
        
        return (f"Created {rel_type.value} relationship between '{source_name}' and '{target_name}'", True)
    
    def _remove_entity(self, details: dict) -> tuple[str, bool]:
        """Remove an entity and all its relationships.
        
        Args:
            details: Should contain 'entity_id'
        """
        entity_id = details.get("entity_id")
        if not entity_id:
            return ("Remove entity requires 'entity_id'", False)
        
        # Find entity
        entity = next((e for e in self.entities if e.id == entity_id), None)
        if not entity:
            return (f"Entity {entity_id} not found", False)
        
        entity_name = entity.descriptor.name if entity.descriptor else entity_id
        
        # Remove all relationships involving this entity
        self.relationships = [
            r for r in self.relationships
            if r.source_id != entity_id and r.target_id != entity_id
        ]
        
        # Remove entity
        self.entities.remove(entity)
        
        return (f"Removed entity '{entity_name}' and all its relationships", True)
    
    def _modify_entity(self, details: dict) -> tuple[str, bool]:
        """Modify an entity's properties.
        
        Args:
            details: Should contain 'entity_id', 'field', and 'value'
        """
        entity_id = details.get("entity_id")
        field = details.get("field", "")
        value = details.get("value", "")
        
        if not entity_id:
            return ("Modify entity requires 'entity_id'", False)
        if not field:
            return ("Modify entity requires 'field'", False)
        
        # Find entity
        entity = next((e for e in self.entities if e.id == entity_id), None)
        if not entity:
            return (f"Entity {entity_id} not found", False)
        
        entity_name = entity.descriptor.name if entity.descriptor else entity_id
        
        # Modify field
        field_lower = field.lower()
        if field_lower in ["bio", "description"]:
            entity.descriptor.bio = value
            return (f"Updated '{entity_name}' description", True)
        elif field_lower == "name":
            entity.descriptor.name = value
            return (f"Updated '{entity_id}' name to '{value}'", True)
        else:
            # Try to modify state resources
            if hasattr(entity, "state") and entity.state:
                try:
                    resources = entity.state.resources
                    resources[field] = value
                    entity.state.resources = resources
                    return (f"Updated '{entity_name}' field '{field}' to '{value}'", True)
                except Exception:
                    return (f"Could not modify field '{field}'", False)
            else:
                return (f"Unknown field '{field}'", False)
    
    def _list_entities(self, details: dict) -> tuple[str, bool]:
        """List entities matching a filter.
        
        Args:
            details: Should contain 'filter' (optional, e.g., 'actors', 'locations', 'all')
        """
        from pyscrai_core import EntityType
        
        filter_str = details.get("filter", "all").lower()
        
        filtered = []
        if filter_str == "all":
            filtered = self.entities
        else:
            # Try to match entity type
            try:
                entity_type = EntityType(filter_str)
                filtered = [e for e in self.entities if e.descriptor.entity_type == entity_type]
            except ValueError:
                # Fallback: search by name
                filter_lower = filter_str.lower()
                filtered = [
                    e for e in self.entities
                    if filter_lower in (e.descriptor.name.lower() if e.descriptor else "")
                ]
        
        if not filtered:
            return (f"No entities found matching '{filter_str}'", True)
        
        lines = [f"Found {len(filtered)} entities:"]
        for e in filtered[:20]:  # Limit to 20 for readability
            name = e.descriptor.name if e.descriptor else e.id
            e_type = e.descriptor.entity_type.value if e.descriptor else "unknown"
            lines.append(f"  • {name} ({e_type}) [ID: {e.id[:8]}...]")
        
        if len(filtered) > 20:
            lines.append(f"  ... and {len(filtered) - 20} more")
        
        return ("\n".join(lines), True)

