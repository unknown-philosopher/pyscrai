"""Prompt Manager for loading and rendering Jinja2 prompt templates."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages Jinja2 prompt templates for LLM interactions."""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize the prompt manager.
        
        Args:
            prompts_dir: Directory containing prompt templates. Defaults to forge/config/prompts/templates/
        """
        if prompts_dir is None:
            # Get prompts directory relative to this file
            prompts_dir = Path(__file__).parent / "templates"
        
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        
        logger.info(f"PromptManager initialized with templates directory: {self.prompts_dir}")
    
    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a prompt template with the given variables.
        
        Args:
            template_name: Name of the template file (without .j2 extension)
            **kwargs: Variables to pass to the template
            
        Returns:
            Rendered prompt string
            
        Raises:
            TemplateNotFound: If the template doesn't exist
        """
        try:
            template = self.env.get_template(f"{template_name}.j2")
            return template.render(**kwargs)
        except TemplateNotFound:
            logger.error(f"Prompt template not found: {template_name}.j2 in {self.prompts_dir}")
            raise
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise
    
    def get_template_path(self, template_name: str) -> Path:
        """Get the full path to a template file.
        
        Args:
            template_name: Name of the template (without .j2 extension)
            
        Returns:
            Path to the template file
        """
        return self.prompts_dir / f"{template_name}.j2"


# Global prompt manager instance
_default_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the default prompt manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = PromptManager()
    return _default_manager


def render_prompt(template_name: str, **kwargs: Any) -> str:
    """Convenience function to render a prompt using the default manager.
    
    Args:
        template_name: Name of the template file (without .j2 extension)
        **kwargs: Variables to pass to the template
        
    Returns:
        Rendered prompt string
    """
    return get_prompt_manager().render(template_name, **kwargs)
