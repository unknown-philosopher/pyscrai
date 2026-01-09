"""
Prefabs - Static user assets and templates.

Organized into:
- schemas/: YAML/JSON templates for Entity/Relationship schemas
- settings/: Reusable configurations (e.g., genre presets)
- templates/: Extraction prompt templates

Provides dynamic schema loading for flexible entity attributes.
"""

from forge.prefabs.schema import PrefabSchema, FieldDefinition, FieldType
from forge.prefabs.loader import PrefabLoader, PrefabRegistry

__all__ = [
    "PrefabSchema",
    "FieldDefinition",
    "FieldType",
    "PrefabLoader",
    "PrefabRegistry",
]
