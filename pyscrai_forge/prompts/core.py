"""Core system prompts and shared definitions for PyScrAI|Forge agents.

This module defines the BASE_SYSTEM_PROMPT and core principles that all agents
must respect. It ensures consistency across the unified Forge architecture.
"""

from dataclasses import dataclass
from enum import Enum

# =============================================================================
# GENRE DEFINITIONS (moved from prompts/core.py original)
# =============================================================================

class Genre(str, Enum):
    """Document genre for context-appropriate extraction."""
    HISTORICAL = "historical"
    FANTASY = "fantasy"
    SCIFI = "scifi"
    MODERN = "modern"
    GENERIC = "generic"

@dataclass
class PromptTemplate:
    """Container for extraction prompt configuration."""
    system_prompt: str
    user_prompt_template: str
    genre: Genre
    target_entities: list[str]

# =============================================================================
# CORE PRINCIPLES
# =============================================================================

BASE_SYSTEM_PROMPT = """You are a PyScrAI|Forge agent operating under core principles:

CORE PRINCIPLES:
1. AGNOSTIC SCALING: You must be able to work at any scale - Macro (Geopolitical), 
   Meso (Tactical), or Micro (Individual). Do not assume a fixed scale.
   
2. DATA-DRIVEN: All outputs must be grounded in provided data. Do not hallucinate 
   or invent information not present in the source material.
   
3. PROJECT-SPECIFIC: Always respect the Project Manifest schema and configuration.
   Adapt your behavior to the specific world being built.

4. GENRE-AWARE: Understand the genre/context (historical, fantasy, scifi, modern) 
   and adjust terminology and approach accordingly.

These principles apply to all PyScrAI|Forge agents.
"""

__all__ = ["BASE_SYSTEM_PROMPT", "Genre", "PromptTemplate"]