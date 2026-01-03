"""PyScrAI Harvester - Entity extraction from raw text.

The Harvester is the "mining rig" that extracts structured entity data
from unstructured source documents (PDFs, text files, wiki pages).

Key Components:
- CLI: Command-line interface for batch processing
- Agents: Multi-agent system for extraction (Scout, Analyst, Validator)
- Prompts: Genre-aware prompt templates for different entity types

Usage:
    python -m pyscrai_forge.src process ./document.txt
"""

# To avoid circular imports, we don't import CLI app here if CLI imports manager
# Users should import app from .cli if needed
# But standard pattern is __main__ calls cli.app()
from ..prompts.core import PromptTemplate
from ..prompts.harvester_prompts import get_scout_prompt
try:
    from .forge import ReviewerApp, main as reviewer_main
except ImportError:
    # If tkinter is missing (e.g. in headless CI/CD), we skip this import
    ReviewerApp = None
    reviewer_main = None

from .storage import (
    commit_extraction_result,
    init_harvester_tables,
    load_all_entities,
    load_all_relationships,
    save_entity,
    save_relationship,
)

from .config_manager import ConfigManager

__all__ = [
    "PromptTemplate",
    "get_scout_prompt",
    "ReviewerApp",
    "reviewer_main",
    "init_harvester_tables",
    "save_entity",
    "save_relationship",
    "load_all_entities",
    "load_all_relationships",
    "commit_extraction_result",
    "ConfigManager",
]
