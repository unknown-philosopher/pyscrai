"""Utilities for working with templates and their schemas."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pyscrai_forge.src.logging_config import get_logger


def get_templates_dir() -> Path:
    """Get the templates directory path.
    
    Returns:
        Path to the templates directory
    """
    # Templates live at pyscrai_forge/prompts/templates (sibling of src)
    return Path(__file__).resolve().parent.parent / 'prompts' / 'templates'


def load_template_schema(template_name: Optional[str]) -> Dict[str, Any]:
    """Load the entity schemas from a template's schema.yaml file.
    
    Args:
        template_name: The template directory name (e.g., 'default', 'espionage').
                       If None or empty, returns an empty schemas dict.
    
    Returns:
        A dict with 'schemas' key containing the template's entity schemas,
        or empty dict if template not found or no schema.yaml exists.
    
    Example:
        >>> schemas = load_template_schema('test')
        >>> schemas['schemas']['actor']
        {'name': '...', 'description': '...', ...}
    """
    logger = get_logger(__name__)
    
    if not template_name:
        return {}
    
    try:
        templates_dir = get_templates_dir()
        template_path = templates_dir / template_name / 'schema.yaml'
        
        if not template_path.exists():
            logger.warning(f"Template schema not found: {template_path}")
            return {}
        
        with open(template_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            logger.warning(f"Template schema is empty: {template_path}")
            return {}
        
        logger.info(f"Loaded template schema from {template_path}")
        return data.get('schemas', {})
    
    except Exception as e:
        logger.error(f"Failed to load template schema for '{template_name}': {e}")
        return {}


def get_available_templates() -> list[str]:
    """Get list of available template directory names.
    
    Returns:
        Sorted list of template directory names
    """
    try:
        templates_dir = get_templates_dir()
        if not templates_dir.exists():
            return []
        
        templates = [
            d for d in os.listdir(templates_dir)
            if os.path.isdir(os.path.join(templates_dir, d))
        ]
        return sorted(templates)
    except Exception:
        return []


def ensure_template_schemas(template_name: Optional[str], current_schemas: Dict[str, Any] | None, logger=None) -> Dict[str, Any]:
    """Return schemas, loading from template if existing schemas are empty.

    Treats schemas as empty if the mapping is empty or all entity types have
    empty definitions (e.g., {"actor": {}, "polity": {}}).
    """

    def _is_empty(schemas: Dict[str, Any] | None) -> bool:
        if not schemas:
            return True
        if isinstance(schemas, dict):
            return all((not v) for v in schemas.values())
        return False

    if not _is_empty(current_schemas):
        return current_schemas or {}

    schemas = load_template_schema(template_name)
    if schemas and logger:
        logger.info(f"Loaded template schemas for template='{template_name}'")
    return schemas or {}
