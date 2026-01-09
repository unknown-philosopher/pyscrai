"""
Prompt Manager - Centralized prompt template loading and rendering.

Loads prompt templates from YAML/Jinja files and provides
a unified interface for accessing them.
"""

from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any

from forge.utils.logging import get_logger

# Optional Jinja2 support
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    HAS_JINJA = True
except ImportError:
    HAS_JINJA = False
    Environment = None

# Optional YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

logger = get_logger("prompts.manager")


class PromptManager:
    """Manages prompt templates for agents and phases.
    
    Supports:
    - Plain text templates with $variable substitution
    - YAML-based prompt definitions
    - Jinja2 templates (if installed)
    
    Usage:
        manager = PromptManager()
        manager.load_directory("prompts/extraction")
        
        prompt = manager.render("extract_entities", document=doc_text)
    """
    
    def __init__(self, base_path: str | Path | None = None):
        """Initialize the prompt manager.
        
        Args:
            base_path: Base directory for prompt templates
        """
        self._templates: dict[str, str] = {}
        self._metadata: dict[str, dict] = {}
        self._jinja_env: Any = None
        
        if base_path:
            self.base_path = Path(base_path)
            if HAS_JINJA:
                self._jinja_env = Environment(
                    loader=FileSystemLoader(str(self.base_path)),
                    autoescape=select_autoescape(['html', 'xml']),
                )
        else:
            self.base_path = None
    
    def register(
        self,
        name: str,
        template: str,
        metadata: dict | None = None,
    ) -> None:
        """Register a prompt template.
        
        Args:
            name: Template name
            template: Template content
            metadata: Optional metadata (description, version, etc.)
        """
        self._templates[name] = template
        if metadata:
            self._metadata[name] = metadata
        logger.debug(f"Registered prompt: {name}")
    
    def get(self, name: str) -> str | None:
        """Get a raw template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template string or None
        """
        return self._templates.get(name)
    
    def render(self, name: str, **kwargs: Any) -> str:
        """Render a template with variables.
        
        Args:
            name: Template name
            **kwargs: Variables to substitute
            
        Returns:
            Rendered prompt string
            
        Raises:
            KeyError: If template not found
        """
        if name not in self._templates:
            raise KeyError(f"Prompt template not found: {name}")
        
        template_str = self._templates[name]
        
        # Try Jinja2 first if available and template has Jinja syntax
        if HAS_JINJA and self._jinja_env and ("{{" in template_str or "{%" in template_str):
            try:
                template = self._jinja_env.from_string(template_str)
                return template.render(**kwargs)
            except Exception as e:
                logger.warning(f"Jinja2 render failed, falling back: {e}")
        
        # Fall back to string.Template
        try:
            return Template(template_str).safe_substitute(**kwargs)
        except Exception as e:
            logger.error(f"Template render failed: {e}")
            return template_str
    
    def load_file(self, file_path: str | Path) -> bool:
        """Load a prompt template from a file.
        
        Args:
            file_path: Path to template file
            
        Returns:
            True if loaded successfully
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"Prompt file not found: {file_path}")
            return False
        
        try:
            suffix = file_path.suffix.lower()
            name = file_path.stem
            
            if suffix in (".yaml", ".yml"):
                data = self._load_yaml(file_path)
                if isinstance(data, dict):
                    template = data.get("template", data.get("prompt", ""))
                    metadata = {k: v for k, v in data.items() if k not in ("template", "prompt")}
                    self.register(name, template, metadata)
                else:
                    self.register(name, str(data))
                    
            elif suffix == ".json":
                data = self._load_json(file_path)
                if isinstance(data, dict):
                    template = data.get("template", data.get("prompt", ""))
                    metadata = {k: v for k, v in data.items() if k not in ("template", "prompt")}
                    self.register(name, template, metadata)
                else:
                    self.register(name, str(data))
                    
            elif suffix in (".txt", ".jinja", ".jinja2", ".j2"):
                content = file_path.read_text(encoding="utf-8")
                self.register(name, content)
                
            else:
                logger.warning(f"Unsupported prompt file format: {suffix}")
                return False
            
            logger.info(f"Loaded prompt from {file_path.name}: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load prompt from {file_path}: {e}")
            return False
    
    def load_directory(self, dir_path: str | Path) -> int:
        """Load all prompts from a directory.
        
        Args:
            dir_path: Path to directory
            
        Returns:
            Number of prompts loaded
        """
        dir_path = Path(dir_path)
        
        if not dir_path.exists():
            logger.warning(f"Prompt directory not found: {dir_path}")
            return 0
        
        count = 0
        patterns = ["*.yaml", "*.yml", "*.json", "*.txt", "*.jinja", "*.jinja2", "*.j2"]
        
        for pattern in patterns:
            for file_path in dir_path.glob(pattern):
                if self.load_file(file_path):
                    count += 1
        
        logger.info(f"Loaded {count} prompts from {dir_path}")
        return count
    
    def list_prompts(self) -> list[str]:
        """List all registered prompt names."""
        return list(self._templates.keys())
    
    def get_metadata(self, name: str) -> dict:
        """Get metadata for a prompt.
        
        Args:
            name: Prompt name
            
        Returns:
            Metadata dict (empty if none)
        """
        return self._metadata.get(name, {})
    
    def _load_yaml(self, file_path: Path) -> Any:
        """Load a YAML file."""
        if not HAS_YAML:
            raise ImportError("YAML support requires pyyaml")
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _load_json(self, file_path: Path) -> Any:
        """Load a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def clear(self) -> None:
        """Clear all registered prompts."""
        self._templates.clear()
        self._metadata.clear()


# ============================================================================
# Built-in Prompt Templates
# ============================================================================


# Extraction prompts
EXTRACTION_SYSTEM = """You are an entity extraction specialist for worldbuilding.
Extract entities (actors, locations, polities, events, objects) from the provided text.
Return structured JSON with entities and relationships."""

EXTRACTION_USER = """Extract entities from this text:

$document

Return JSON with:
{
  "entities": [{"name": "", "type": "", "description": "", "aliases": []}],
  "relationships": [{"source": "", "target": "", "type": "", "description": ""}]
}"""

# Analysis prompts
ANALYSIS_ENTITY = """Analyze this entity in depth:

Name: $name
Type: $type
Description: $description

Provide:
1. Key characteristics
2. Potential motivations
3. Narrative importance
4. Suggested connections"""

ANALYSIS_RELATIONSHIP = """Analyze this relationship:

Source: $source_name ($source_type)
Target: $target_name ($target_type)
Type: $relationship_type
Strength: $strength

Provide:
1. Relationship dynamics
2. Story implications
3. Potential conflicts
4. Evolution possibilities"""


def create_default_manager() -> PromptManager:
    """Create a prompt manager with built-in defaults.
    
    Returns:
        PromptManager with default prompts registered
    """
    manager = PromptManager()
    
    # Register built-in prompts
    manager.register("extraction_system", EXTRACTION_SYSTEM, {"category": "extraction"})
    manager.register("extraction_user", EXTRACTION_USER, {"category": "extraction"})
    manager.register("analysis_entity", ANALYSIS_ENTITY, {"category": "analysis"})
    manager.register("analysis_relationship", ANALYSIS_RELATIONSHIP, {"category": "analysis"})
    
    return manager
