"""Template Manager: Load and manage prompt templates.

This system allows organizing prompts as reusable templates that can be
selected by genre, project type, or custom preference. Templates are stored
as YAML files for easy editing.

Usage:
    manager = TemplateManager()
    
    # Get scout template for historical genre
    template = manager.get_template("scout", genre="historical")
    system, user = template.render(text="...", genre="historical")
    
    # List available templates
    templates = manager.list_templates("scout")
    
    # Register custom template
    manager.register_template("scout", "custom", CustomTemplate())
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """A prompt template with system and user prompts."""
    name: str
    description: str
    version: str
    system_prompt: str
    user_prompt_template: str  # Can contain {placeholders}
    metadata: Dict = None
    
    def render(self, **kwargs) -> Tuple[str, str]:
        """Render the template with provided variables.
        
        Args:
            **kwargs: Variables to substitute in templates (e.g., text, genre, entities)
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Safe formatting: only substitute variables that are provided
        def safe_format(template: str, variables: dict) -> str:
            """Format template, only replacing placeholders that exist in variables."""
            if not template or "{" not in template:
                return template
            
            # Use partial formatting - only format keys we have
            import string
            formatter = string.Formatter()
            result = []
            
            for literal_text, field_name, format_spec, conversion in formatter.parse(template):
                result.append(literal_text)
                if field_name is not None:
                    if field_name in variables:
                        value = variables[field_name]
                        if conversion:
                            value = format(value, format_spec) if format_spec else str(value)
                        result.append(str(value))
                    else:
                        # Keep placeholder as-is if variable not provided
                        result.append("{" + field_name + (":" + format_spec if format_spec else "") + "}")
            
            return "".join(result)
        
        system = safe_format(self.system_prompt, kwargs)
        user = safe_format(self.user_prompt_template, kwargs)
        return system, user


@dataclass
class SchemaTemplate:
    """An entity schema template defining fields for each entity type."""
    name: str
    description: str
    version: str
    genre: str
    schemas: Dict[str, Dict[str, str]]  # {entity_type: {field: description}}
    metadata: Dict = None
    
    def get_schema(self, entity_type: str) -> Dict[str, str]:
        """Get the schema for a specific entity type.
        
        Args:
            entity_type: Type of entity (actor, polity, location, abstract)
            
        Returns:
            Dictionary of {field: description}
        """
        return self.schemas.get(entity_type, {})
    
    def get_all_schemas(self) -> Dict[str, Dict[str, str]]:
        """Get all schemas."""
        return self.schemas


class TemplateManager:
    """Manages prompt templates across different genres and use cases."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template manager.
        
        Args:
            template_dir: Path to templates directory. Defaults to pyscrai_forge/prompts/templates/
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        
        self.template_dir = template_dir
        self._prompt_cache: Dict[str, Dict[str, PromptTemplate]] = {}
        self._schema_cache: Dict[str, SchemaTemplate] = {}
        self._custom_prompts: Dict[str, Dict[str, PromptTemplate]] = {}
        self._custom_schemas: Dict[str, SchemaTemplate] = {}
    
    def get_template(
        self, 
        agent_type: str,  # "scout", "analyst", "relationships", etc
        genre: str = "default",
        custom_name: Optional[str] = None,
        allow_fallback: bool = True
    ) -> PromptTemplate:
        """Get a prompt template.
        
        Lookup order:
        1. Custom templates (if registered)
        2. Genre-specific template (e.g., historical/scout.yaml)
        3. Default template (e.g., default/scout.yaml) - only if allow_fallback=True
        
        Args:
            agent_type: Type of agent ("scout", "analyst", "relationships")
            genre: Genre or category ("default", "historical", "espionage", etc)
            custom_name: Optional custom template name (overrides genre)
            allow_fallback: If True, fallback to "default" template if genre-specific not found.
                           If False, raise FileNotFoundError if genre-specific template not found.
            
        Returns:
            PromptTemplate instance
            
        Raises:
            FileNotFoundError: If template not found
        """
        # Check custom templates first
        if custom_name and custom_name in self._custom_prompts.get(agent_type, {}):
            logger.info(f"TemplateManager: Using custom template '{custom_name}' for agent_type='{agent_type}'")
            return self._custom_prompts[agent_type][custom_name]
        
        # Try genre-specific template first
        template_path = self.template_dir / genre / f"{agent_type}.yaml"
        logger.info(f"TemplateManager: Looking for template at {template_path} (allow_fallback={allow_fallback})")
        
        if template_path.exists():
            logger.info(f"TemplateManager: Found template at {template_path}")
            # Load from cache if available
            cache_key = f"{genre}/{agent_type}"
            if cache_key not in self._prompt_cache.get(agent_type, {}):
                logger.info(f"TemplateManager: Loading template from disk (not in cache)")
                self._prompt_cache.setdefault(agent_type, {})[cache_key] = self._load_prompt_template(template_path)
            else:
                logger.info(f"TemplateManager: Using cached template")
            
            return self._prompt_cache[agent_type][cache_key]
        
        # Fallback to default only if allowed
        if allow_fallback and genre != "default":
            default_path = self.template_dir / "default" / f"{agent_type}.yaml"
            logger.info(f"TemplateManager: Template not found at {template_path}, trying fallback to {default_path}")
            if default_path.exists():
                logger.info(f"TemplateManager: Found fallback template at {default_path}")
                cache_key = f"default/{agent_type}"
                if cache_key not in self._prompt_cache.get(agent_type, {}):
                    logger.info(f"TemplateManager: Loading fallback template from disk (not in cache)")
                    self._prompt_cache.setdefault(agent_type, {})[cache_key] = self._load_prompt_template(default_path)
                else:
                    logger.info(f"TemplateManager: Using cached fallback template")
                
                return self._prompt_cache[agent_type][cache_key]
        
        logger.error(
            f"TemplateManager: Template not found for agent_type='{agent_type}', genre='{genre}'. "
            f"Tried: {template_path}"
            + (f" and {self.template_dir / 'default' / f'{agent_type}.yaml'}" if allow_fallback else "")
        )
        raise FileNotFoundError(
            f"Template not found for agent_type='{agent_type}', genre='{genre}'. "
            f"Tried: {template_path}"
            + (f" and {self.template_dir / 'default' / f'{agent_type}.yaml'}" if allow_fallback else "")
        )
    
    def list_templates(self, agent_type: str) -> Dict[str, list]:
        """List available templates for an agent type.
        
        Returns:
            Dict with keys for each available genre
        """
        if not self.template_dir.exists():
            return {}
        
        templates = {}
        for genre_dir in self.template_dir.iterdir():
            if genre_dir.is_dir():
                template_file = genre_dir / f"{agent_type}.yaml"
                if template_file.exists():
                    if genre_dir.name not in templates:
                        templates[genre_dir.name] = []
                    templates[genre_dir.name].append(agent_type)
        
        return templates
    
    def register_custom_template(
        self,
        agent_type: str,
        name: str,
        template: PromptTemplate
    ):
        """Register a custom prompt template at runtime.
        
        Args:
            agent_type: Type of agent
            name: Custom template name
            template: PromptTemplate instance
        """
        if agent_type not in self._custom_prompts:
            self._custom_prompts[agent_type] = {}
        self._custom_prompts[agent_type][name] = template
    
    def get_schema(
        self,
        genre: str = "default",
        custom_name: Optional[str] = None
    ) -> SchemaTemplate:
        """Get an entity schema template.
        
        Lookup order:
        1. Custom schemas (if registered)
        2. Genre-specific schema (e.g., historical/schema.yaml)
        3. Default schema
        
        Args:
            genre: Genre or category ("default", "historical", "espionage", etc)
            custom_name: Optional custom schema name (overrides genre)
            
        Returns:
            SchemaTemplate instance
            
        Raises:
            FileNotFoundError: If schema not found
        """
        # Check custom schemas first
        if custom_name and custom_name in self._custom_schemas:
            return self._custom_schemas[custom_name]
        
        # Try genre-specific, then default
        for template_genre in [genre, "default"]:
            schema_path = self.template_dir / template_genre / "schema.yaml"
            
            if schema_path.exists():
                cache_key = f"{template_genre}_schema"
                if cache_key not in self._schema_cache:
                    self._schema_cache[cache_key] = self._load_schema_template(schema_path)
                return self._schema_cache[cache_key]
        
        raise FileNotFoundError(
            f"Schema template not found for genre='{genre}'. "
            f"Tried: {self.template_dir / genre / 'schema.yaml'}"
        )
    
    def register_custom_schema(self, name: str, schema: SchemaTemplate):
        """Register a custom entity schema template at runtime.
        
        Args:
            name: Custom schema name
            schema: SchemaTemplate instance
        """
        self._custom_schemas[name] = schema
    
    def _load_prompt_template(self, path: Path) -> PromptTemplate:
        """Load a prompt template from YAML file.
        
        Args:
            path: Path to template YAML file
            
        Returns:
            PromptTemplate instance
            
        Raises:
            ValueError: If template file is empty or malformed
        """
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {path}")
        
        # Check if file is empty
        if path.stat().st_size == 0:
            raise ValueError(f"Template file is empty: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Validate that data was loaded (not None or empty)
        if not data:
            raise ValueError(f"Template file is empty or contains no valid YAML: {path}")
        
        # Validate required fields
        system_prompt = data.get('system_prompt', '')
        user_prompt_template = data.get('user_prompt_template', '')
        
        if not system_prompt and not user_prompt_template:
            raise ValueError(
                f"Template file is missing required prompts (system_prompt and user_prompt_template are both empty): {path}"
            )
        
        if not system_prompt:
            raise ValueError(f"Template file is missing system_prompt: {path}")
        
        if not user_prompt_template:
            raise ValueError(f"Template file is missing user_prompt_template: {path}")
        
        return PromptTemplate(
            name=data.get('name', path.stem),
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            metadata=data.get('metadata', {})
        )
    
    def _load_schema_template(self, path: Path) -> SchemaTemplate:
        """Load a schema template from YAML file.
        
        Args:
            path: Path to schema YAML file
            
        Returns:
            SchemaTemplate instance
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return SchemaTemplate(
            name=data.get('name', path.parent.name),
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            genre=data.get('genre', path.parent.name),
            schemas=data.get('schemas', {}),
            metadata=data.get('metadata', {})
        )
    
    def reload_cache(self):
        """Clear the template cache to force reload from disk."""
        self._prompt_cache.clear()
        self._schema_cache.clear()
    
    def export_prompt_template_to_file(
        self,
        agent_type: str,
        genre: str,
        output_path: Path
    ):
        """Export a prompt template to a new file.
        
        Useful for creating new genre templates from existing ones.
        
        Args:
            agent_type: Type of agent
            genre: Genre of template to export
            output_path: Where to save the exported template
        """
        template = self.get_template(agent_type, genre)
        
        data = {
            'name': template.name,
            'description': template.description,
            'version': template.version,
            'system_prompt': template.system_prompt,
            'user_prompt_template': template.user_prompt_template,
            'metadata': template.metadata or {}
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"Prompt template exported to: {output_path}")
    
    def export_schema_to_file(
        self,
        genre: str,
        output_path: Path
    ):
        """Export a schema template to a new file.
        
        Args:
            genre: Genre of schema to export
            output_path: Where to save the exported schema
        """
        schema = self.get_schema(genre)
        
        data = {
            'name': schema.name,
            'description': schema.description,
            'version': schema.version,
            'genre': schema.genre,
            'schemas': schema.schemas,
            'metadata': schema.metadata or {}
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"Schema template exported to: {output_path}")


__all__ = ["TemplateManager", "PromptTemplate", "SchemaTemplate"]
