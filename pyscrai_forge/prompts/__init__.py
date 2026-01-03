"""PyScrAI|Forge Prompt System.

Centralized prompt repository for all agents.
"""

# Core prompts
from .core import BASE_SYSTEM_PROMPT, Genre, PromptTemplate

# Analysis prompts
from .analysis import (
    ANALYST_SYSTEM_PROMPT,
    SYSTEM_PROMPT_ANALYST_EXTRACTION,
    JSON_REFINER_PROMPT,
    build_extraction_prompt,
    build_refinement_prompt,
)

# Narrative prompts
from .narrative import (
    NARRATOR_SYSTEM_PROMPT,
    NARRATIVE_SYSTEM_PROMPT,
    build_possession_system_prompt,
    build_scenario_prompt,
    build_possession_prompt,
)

# Legacy exports for backward compatibility during transition
from . import harvester_prompts
from . import architect_prompts

__all__ = [
    # Core
    "BASE_SYSTEM_PROMPT",
    "Genre",
    "PromptTemplate",
    # Analysis
    "ANALYST_SYSTEM_PROMPT",
    "SYSTEM_PROMPT_ANALYST_EXTRACTION",
    "JSON_REFINER_PROMPT",
    "build_extraction_prompt",
    "build_refinement_prompt",
    # Narrative
    "NARRATOR_SYSTEM_PROMPT",
    "NARRATIVE_SYSTEM_PROMPT",
    "build_possession_system_prompt",
    "build_scenario_prompt",
    "build_possession_prompt",
    # Legacy (for transition)
    "harvester_prompts",
    "architect_prompts",
]
