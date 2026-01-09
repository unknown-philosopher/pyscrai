"""
Prompts - Centralized prompt storage and template management.

Organized into:
- advisors/: Phase-specific advisor prompts (OSINT, HUMINT, SIGINT, SYNTH, GEOINT, ANVIL)
- extraction.yaml: Entity/relationship extraction prompts
- analysis.yaml: Deep analysis prompts
- review.yaml: QA and review prompts
"""

from pathlib import Path
from forge.agents.prompts.manager import PromptManager

# Initialize default manager with prompts directory
_PROMPTS_DIR = Path(__file__).parent
_ADVISORS_DIR = _PROMPTS_DIR / "advisors"
_DEFAULT_MANAGER = PromptManager(base_path=_PROMPTS_DIR)

# Load all YAML prompt files from main directory
_DEFAULT_MANAGER.load_directory(_PROMPTS_DIR)

# Load advisor prompts from subdirectory
if _ADVISORS_DIR.exists():
    _DEFAULT_MANAGER.load_directory(_ADVISORS_DIR)

def get_prompt_manager() -> PromptManager:
    """Get the default prompt manager with all templates pre-loaded."""
    return _DEFAULT_MANAGER

__all__ = ["PromptManager", "get_prompt_manager"]
