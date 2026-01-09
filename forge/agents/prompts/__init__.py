"""
Prompts - Centralized prompt storage and template management.

Organized into:
- advisors/: Advisor-specific YAML/Jinja templates
- extraction/: Phase 0 extraction prompts
- analysis/: General analysis/reasoning prompts
"""

from forge.agents.prompts.manager import PromptManager

__all__ = ["PromptManager"]
