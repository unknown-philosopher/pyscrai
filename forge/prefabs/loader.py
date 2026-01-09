"""
Prefab Loader for Forge 3.0.

Loads prefab schemas from YAML/JSON files and manages the registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from forge.prefabs.schema import (
    PrefabSchema,
    get_default_actor_schema,
    get_default_location_schema,
    get_default_polity_schema,
)
from forge.utils.logging import get_logger

# Optional YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

logger = get_logger("prefabs.loader")


class PrefabRegistry:
    """Registry of loaded prefab schemas.
    
    Provides centralized access to all available schemas,
    with support for built-in defaults and custom schemas.
    
    Usage:
        registry = PrefabRegistry()
        registry.load_defaults()
        registry.load_from_directory("./schemas")
        
        schema = registry.get("actor_espionage")
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._schemas: dict[str, PrefabSchema] = {}
    
    def register(self, schema: PrefabSchema) -> None:
        """Register a schema.
        
        Args:
            schema: Schema to register
        """
        self._schemas[schema.name] = schema
        logger.debug(f"Registered schema: {schema.name}")
    
    def get(self, name: str) -> PrefabSchema | None:
        """Get a schema by name.
        
        Args:
            name: Schema name
            
        Returns:
            Schema or None if not found
        """
        return self._schemas.get(name)
    
    def get_for_entity_type(self, entity_type: str) -> list[PrefabSchema]:
        """Get all schemas for an entity type.
        
        Args:
            entity_type: Entity type (e.g., "ACTOR")
            
        Returns:
            List of matching schemas
        """
        return [
            s for s in self._schemas.values()
            if s.entity_type.upper() == entity_type.upper()
        ]
    
    def list_schemas(self) -> list[str]:
        """List all registered schema names."""
        return list(self._schemas.keys())
    
    def iterate(self) -> Iterator[PrefabSchema]:
        """Iterate over all schemas."""
        yield from self._schemas.values()
    
    def load_defaults(self) -> None:
        """Load built-in default schemas."""
        self.register(get_default_actor_schema())
        self.register(get_default_location_schema())
        self.register(get_default_polity_schema())
        logger.info("Loaded default schemas")
    
    def clear(self) -> None:
        """Clear all registered schemas."""
        self._schemas.clear()
    
    def to_dict(self) -> dict:
        """Export registry to dictionary."""
        return {
            name: schema.to_dict()
            for name, schema in self._schemas.items()
        }


class PrefabLoader:
    """Loads prefab schemas from files.
    
    Supports JSON and YAML (if pyyaml installed) formats.
    
    Usage:
        loader = PrefabLoader(registry)
        loader.load_file("schemas/actor_espionage.yaml")
        loader.load_directory("schemas/")
    """
    
    def __init__(self, registry: PrefabRegistry):
        """Initialize the loader.
        
        Args:
            registry: Registry to load schemas into
        """
        self.registry = registry
    
    def load_file(self, file_path: str | Path) -> PrefabSchema | None:
        """Load a schema from a file.
        
        Args:
            file_path: Path to the schema file
            
        Returns:
            Loaded schema, or None if failed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"Schema file not found: {file_path}")
            return None
        
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == ".json":
                data = self._load_json(file_path)
            elif suffix in (".yaml", ".yml"):
                data = self._load_yaml(file_path)
            else:
                logger.warning(f"Unsupported file format: {suffix}")
                return None
            
            schema = PrefabSchema.from_dict(data)
            
            # Handle inheritance
            if schema.inherits:
                parent = self.registry.get(schema.inherits)
                if parent:
                    schema = self._apply_inheritance(schema, parent)
            
            self.registry.register(schema)
            logger.info(f"Loaded schema from {file_path.name}: {schema.name}")
            
            return schema
            
        except Exception as e:
            logger.error(f"Failed to load schema from {file_path}: {e}")
            return None
    
    def load_directory(self, dir_path: str | Path) -> list[PrefabSchema]:
        """Load all schemas from a directory.
        
        Args:
            dir_path: Path to the directory
            
        Returns:
            List of loaded schemas
        """
        dir_path = Path(dir_path)
        
        if not dir_path.exists():
            logger.warning(f"Schema directory not found: {dir_path}")
            return []
        
        schemas = []
        
        # Load JSON files
        for file_path in dir_path.glob("*.json"):
            schema = self.load_file(file_path)
            if schema:
                schemas.append(schema)
        
        # Load YAML files
        for pattern in ("*.yaml", "*.yml"):
            for file_path in dir_path.glob(pattern):
                schema = self.load_file(file_path)
                if schema:
                    schemas.append(schema)
        
        logger.info(f"Loaded {len(schemas)} schemas from {dir_path}")
        return schemas
    
    def _load_json(self, file_path: Path) -> dict:
        """Load a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _load_yaml(self, file_path: Path) -> dict:
        """Load a YAML file."""
        if not HAS_YAML:
            raise ImportError(
                "YAML support requires pyyaml. Install with: pip install pyyaml"
            )
        
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _apply_inheritance(
        self,
        child: PrefabSchema,
        parent: PrefabSchema,
    ) -> PrefabSchema:
        """Apply inheritance from parent schema.
        
        Args:
            child: Child schema
            parent: Parent schema to inherit from
            
        Returns:
            Merged schema
        """
        # Combine fields (child overrides parent)
        parent_fields = {f.name: f for f in parent.fields}
        child_fields = {f.name: f for f in child.fields}
        
        merged_fields = list(parent_fields.values())
        for name, field in child_fields.items():
            if name in parent_fields:
                # Replace parent field
                merged_fields = [
                    field if f.name == name else f
                    for f in merged_fields
                ]
            else:
                merged_fields.append(field)
        
        return PrefabSchema(
            name=child.name,
            entity_type=child.entity_type or parent.entity_type,
            label=child.label or parent.label,
            description=child.description or parent.description,
            fields=merged_fields,
            inherits=None,  # Clear inheritance after applying
            metadata={**parent.metadata, **child.metadata},
        )
    
    def save_schema(
        self,
        schema: PrefabSchema,
        file_path: str | Path,
        format: str = "json",
    ) -> None:
        """Save a schema to a file.
        
        Args:
            schema: Schema to save
            file_path: Path to save to
            format: Output format ("json" or "yaml")
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = schema.to_dict()
        
        if format == "yaml" and HAS_YAML:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved schema to {file_path}")


# ============================================================================
# Convenience Functions
# ============================================================================


def load_project_schemas(
    project_path: str | Path,
    include_defaults: bool = True,
) -> PrefabRegistry:
    """Load schemas for a project.
    
    Args:
        project_path: Path to project directory
        include_defaults: Whether to include built-in defaults
        
    Returns:
        Populated registry
    """
    registry = PrefabRegistry()
    
    if include_defaults:
        registry.load_defaults()
    
    loader = PrefabLoader(registry)
    
    # Look for schemas in project
    project_path = Path(project_path)
    schemas_dir = project_path / "schemas"
    
    if schemas_dir.exists():
        loader.load_directory(schemas_dir)
    
    return registry


def create_global_registry() -> PrefabRegistry:
    """Create a global registry with defaults.
    
    Returns:
        Registry with default schemas
    """
    registry = PrefabRegistry()
    registry.load_defaults()
    return registry
