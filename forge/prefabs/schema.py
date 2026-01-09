"""
Prefab Schema Definitions for Forge 3.0.

Defines the structure of entity schemas that can be loaded
from YAML/JSON files to customize entity attributes per project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldType(str, Enum):
    """Supported field types for schema definitions."""
    
    STRING = "string"
    TEXT = "text"  # Multi-line string
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"  # Choice from options
    REFERENCE = "reference"  # Reference to another entity


@dataclass
class FieldDefinition:
    """Definition of a single field in a schema.
    
    Attributes:
        name: Field name (key in attributes dict)
        type: Data type of the field
        label: Human-readable label for UI
        description: Help text for the field
        required: Whether field is required
        default: Default value if not provided
        options: For enum type, list of valid options
        reference_type: For reference type, the entity type to reference
        validators: List of validation rule names
    """
    
    name: str
    type: FieldType
    label: str = ""
    description: str = ""
    required: bool = False
    default: Any = None
    options: list[str] = field(default_factory=list)
    reference_type: str | None = None
    validators: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.label:
            self.label = self.name.replace("_", " ").title()
    
    @classmethod
    def from_dict(cls, data: dict) -> "FieldDefinition":
        """Create from dictionary."""
        field_type = FieldType(data.get("type", "string"))
        
        return cls(
            name=data["name"],
            type=field_type,
            label=data.get("label", ""),
            description=data.get("description", ""),
            required=data.get("required", False),
            default=data.get("default"),
            options=data.get("options", []),
            reference_type=data.get("reference_type"),
            validators=data.get("validators", []),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "type": self.type.value,
            "label": self.label,
            "required": self.required,
        }
        
        if self.description:
            result["description"] = self.description
        if self.default is not None:
            result["default"] = self.default
        if self.options:
            result["options"] = self.options
        if self.reference_type:
            result["reference_type"] = self.reference_type
        if self.validators:
            result["validators"] = self.validators
        
        return result
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate a value against this field definition.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            if self.required:
                return False, f"Field '{self.name}' is required"
            return True, ""
        
        # Type checking
        if self.type == FieldType.STRING or self.type == FieldType.TEXT:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be a string"
        
        elif self.type == FieldType.INT:
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"Field '{self.name}' must be an integer"
        
        elif self.type == FieldType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"Field '{self.name}' must be a number"
        
        elif self.type == FieldType.BOOL:
            if not isinstance(value, bool):
                return False, f"Field '{self.name}' must be a boolean"
        
        elif self.type == FieldType.LIST:
            if not isinstance(value, list):
                return False, f"Field '{self.name}' must be a list"
        
        elif self.type == FieldType.DICT:
            if not isinstance(value, dict):
                return False, f"Field '{self.name}' must be a dictionary"
        
        elif self.type == FieldType.ENUM:
            if self.options and value not in self.options:
                return False, f"Field '{self.name}' must be one of: {self.options}"
        
        return True, ""


@dataclass
class PrefabSchema:
    """Schema definition for an entity type.
    
    Defines the structure of attributes for a specific entity type,
    allowing projects to customize what data is captured.
    
    Attributes:
        name: Schema identifier (e.g., "actor_espionage")
        entity_type: The entity type this schema applies to
        label: Human-readable name
        description: Schema description
        fields: List of field definitions
        inherits: Optional parent schema to inherit from
        metadata: Additional schema metadata
    """
    
    name: str
    entity_type: str
    label: str = ""
    description: str = ""
    fields: list[FieldDefinition] = field(default_factory=list)
    inherits: str | None = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.label:
            self.label = self.name.replace("_", " ").title()
    
    @classmethod
    def from_dict(cls, data: dict) -> "PrefabSchema":
        """Create schema from dictionary."""
        fields = [
            FieldDefinition.from_dict(f) if isinstance(f, dict) else f
            for f in data.get("fields", [])
        ]
        
        return cls(
            name=data["name"],
            entity_type=data.get("entity_type", "CUSTOM"),
            label=data.get("label", ""),
            description=data.get("description", ""),
            fields=fields,
            inherits=data.get("inherits"),
            metadata=data.get("metadata", {}),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "label": self.label,
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
            "inherits": self.inherits,
            "metadata": self.metadata,
        }
    
    def get_field(self, name: str) -> FieldDefinition | None:
        """Get a field by name."""
        for f in self.fields:
            if f.name == name:
                return f
        return None
    
    def get_required_fields(self) -> list[FieldDefinition]:
        """Get all required fields."""
        return [f for f in self.fields if f.required]
    
    def get_default_values(self) -> dict[str, Any]:
        """Get default values for all fields."""
        return {
            f.name: f.default
            for f in self.fields
            if f.default is not None
        }
    
    def validate(self, attributes: dict) -> list[tuple[str, str]]:
        """Validate attributes against this schema.
        
        Args:
            attributes: Attribute dict to validate
            
        Returns:
            List of (field_name, error_message) tuples for errors
        """
        errors = []
        
        for field_def in self.fields:
            value = attributes.get(field_def.name)
            is_valid, error = field_def.validate(value)
            if not is_valid:
                errors.append((field_def.name, error))
        
        return errors
    
    def to_prompt_description(self) -> str:
        """Generate a description for LLM prompts.
        
        Returns:
            Schema description suitable for extraction prompts
        """
        lines = [
            f"Schema: {self.label}",
            f"Type: {self.entity_type}",
            "",
            "Fields:",
        ]
        
        for f in self.fields:
            req = " (required)" if f.required else ""
            lines.append(f"- {f.name} ({f.type.value}){req}: {f.description or f.label}")
            if f.options:
                lines.append(f"  Options: {', '.join(f.options)}")
        
        return "\n".join(lines)


# ============================================================================
# Built-in Schemas
# ============================================================================


def get_default_actor_schema() -> PrefabSchema:
    """Get the default actor schema."""
    return PrefabSchema(
        name="actor_default",
        entity_type="ACTOR",
        label="Actor (Default)",
        description="Default schema for actors/characters",
        fields=[
            FieldDefinition(
                name="role",
                type=FieldType.STRING,
                label="Role/Title",
                description="Primary role or title",
            ),
            FieldDefinition(
                name="affiliation",
                type=FieldType.STRING,
                label="Affiliation",
                description="Primary organization affiliation",
            ),
            FieldDefinition(
                name="status",
                type=FieldType.ENUM,
                label="Status",
                options=["active", "inactive", "unknown", "deceased"],
                default="unknown",
            ),
            FieldDefinition(
                name="nationality",
                type=FieldType.STRING,
                label="Nationality",
            ),
            FieldDefinition(
                name="first_appearance",
                type=FieldType.STRING,
                label="First Appearance",
                description="When/where first mentioned",
            ),
        ],
    )


def get_default_location_schema() -> PrefabSchema:
    """Get the default location schema."""
    return PrefabSchema(
        name="location_default",
        entity_type="LOCATION",
        label="Location (Default)",
        description="Default schema for locations",
        fields=[
            FieldDefinition(
                name="location_type",
                type=FieldType.ENUM,
                label="Type",
                options=["city", "country", "region", "building", "site", "other"],
            ),
            FieldDefinition(
                name="country",
                type=FieldType.STRING,
                label="Country",
            ),
            FieldDefinition(
                name="coordinates",
                type=FieldType.STRING,
                label="Coordinates",
                description="Geographic coordinates if known",
            ),
            FieldDefinition(
                name="significance",
                type=FieldType.TEXT,
                label="Significance",
                description="Why this location is significant",
            ),
        ],
    )


def get_default_polity_schema() -> PrefabSchema:
    """Get the default polity/organization schema."""
    return PrefabSchema(
        name="polity_default",
        entity_type="POLITY",
        label="Organization (Default)",
        description="Default schema for organizations/polities",
        fields=[
            FieldDefinition(
                name="org_type",
                type=FieldType.ENUM,
                label="Organization Type",
                options=["government", "military", "corporate", "ngo", "criminal", "other"],
            ),
            FieldDefinition(
                name="headquarters",
                type=FieldType.STRING,
                label="Headquarters",
            ),
            FieldDefinition(
                name="size",
                type=FieldType.STRING,
                label="Size",
                description="Approximate size/membership",
            ),
            FieldDefinition(
                name="founding_date",
                type=FieldType.STRING,
                label="Founded",
            ),
            FieldDefinition(
                name="ideology",
                type=FieldType.TEXT,
                label="Ideology/Mission",
            ),
        ],
    )
