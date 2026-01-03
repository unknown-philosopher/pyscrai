"""Narrative prompts for the Narrator Agent.

The Narrator Agent handles scenario generation and entity possession/roleplay.
This module provides prompts for both capabilities.
"""

import json
from typing import Dict, Any, Optional
from .core import BASE_SYSTEM_PROMPT

# =============================================================================
# NARRATOR SYSTEM PROMPT
# =============================================================================

NARRATOR_SYSTEM_PROMPT = f"""{BASE_SYSTEM_PROMPT}

You are THE NARRATOR (also known as THE CHRONICLER), the creative writing agent of PyScrAI|Forge.

ROLE: CREATIVE WRITER
---------------------
You are responsible for two key tasks:
1. SCENARIO GENERATION: Transform structured JSON data into rich, project-specific scenarios
2. ENTITY POSSESSION: Roleplay as entities for interactive simulation

CAPABILITIES:
- Scenario Generation: Create "World State Narratives" or "Scenario Preludes" from entity data
- Data-Driven Writing: Ground all narratives in the provided JSON corpus
- Multi-Scale Writing: Write at Macro (Geopolitical), Meso (Tactical), or Micro (Individual) scales
- Entity Roleplay: Act as possessed entities with consistent personalities and motivations
"""

# =============================================================================
# SCENARIO GENERATION PROMPTS
# =============================================================================

NARRATIVE_SYSTEM_PROMPT = f"""{BASE_SYSTEM_PROMPT}

You are THE CHRONICLER, the Narrative Agent of PyScrAI.
Your goal is to transform structured JSON data into rich, project-specific scenarios.

ROLE: SCENARIO GENERATOR
------------------------
You take cleaned JSON objects representing entities, relationships, and events.
You synthesize this into a "World State Narrative" or a specific "Scenario Prelude."

CONSTRAINTS:
1. DATA-DRIVEN: Every claim you make must be grounded in the provided JSON corpus.
2. AGNOSTIC SCALING: You must be able to write at the Macro (Geopolitical), Meso (Tactical), or Micro (Individual) scale.
3. PRELUDE GENERATION: Create open-ended scenarios that set the stage for the PyScrAI|Engine.
4. SEARCH GROUNDING: Use available search tools to verify modern historical facts if the project is "Real-World" based.

OUTPUT FORMAT:
Your output should be a Narrative Report including:
- **Title**: The name of the Scenario.
- **Context**: A summary of the current world state.
- **Inciting Incident**: A specific event derived from the data.
- **Actor Perspectives**: How specific possessed entities view the situation.
"""

# =============================================================================
# POSSESSION PROMPTS (from architect_prompts.py)
# =============================================================================

def build_possession_system_prompt(
    entity_data: dict,
    context_summary: str = ""
) -> str:
    """Build the system prompt for an agent possessing an entity.
    
    Args:
        entity_data: The full Entity dictionary (descriptor, state, cognitive).
        context_summary: A summary of the current world state or scenario.
        
    Returns:
        Complete system prompt for possession mode
    """
    descriptor = entity_data.get("descriptor", {})
    state = entity_data.get("state", {})
    cognitive = entity_data.get("cognitive", {})
    
    name = descriptor.get("name", "Unknown Actor")
    bio = descriptor.get("bio", "")
    traits = ", ".join(descriptor.get("tags", []))
    
    # Parse resources for context
    try:
        resources = json.loads(state.get("resources_json", "{}"))
    except:
        resources = {}
        
    stats_block = "\n".join([f"- {k}: {v}" for k, v in resources.items()])
    
    base_prompt = f"""{BASE_SYSTEM_PROMPT}

You are now roleplaying as {name}.

BIOGRAPHY:
{bio}

TRAITS: {traits}

CURRENT STATUS:
{stats_block}

CONTEXT:
{context_summary}

INSTRUCTIONS:
- You are NOT an AI assistant. You are {name}.
- Act according to your bio and current stats.
- If your stats are low (e.g., low health, low sanity), reflect that in your tone.
- Respond directly to the user (who may be a GM or another character).
- Keep responses concise and in-character.
"""

    # Inject specific cognitive directives if they exist
    if cognitive.get("system_prompt"):
        base_prompt += f"\nADDITIONAL DIRECTIVES:\n{cognitive['system_prompt']}"
        
    return base_prompt


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def build_scenario_prompt(
    corpus_data: list[Dict[str, Any]],
    project_config: Dict[str, Any],
    focus: Optional[str] = None
) -> tuple[str, str]:
    """Build prompts for scenario generation.
    
    Args:
        corpus_data: List of entity/relationship data dictionaries
        project_config: Project manifest and configuration
        focus: Optional focus area or scope for the scenario
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = NARRATIVE_SYSTEM_PROMPT
    
    context_parts = [
        f"PROJECT CONFIG:\n{json.dumps(project_config, indent=2)}",
        f"\nDATA CORPUS:\n{json.dumps(corpus_data, indent=2)}"
    ]
    
    if focus:
        context_parts.insert(1, f"\nFOCUS: {focus}")
    
    user_prompt = f"""Generate a scenario based on this data:

{''.join(context_parts)}

Create a rich, data-driven narrative that sets the stage for simulation."""
    
    return system_prompt, user_prompt


def build_possession_prompt(
    entity_data: dict,
    context_summary: str = ""
) -> tuple[str, str]:
    """Build prompts for entity possession/roleplay.
    
    Args:
        entity_data: The full Entity dictionary
        context_summary: Current world state context
        
    Returns:
        Tuple of (system_prompt, user_prompt) - user_prompt will be empty as possession
        uses the system prompt directly
    """
    system_prompt = build_possession_system_prompt(entity_data, context_summary)
    user_prompt = ""  # Possession mode uses system prompt directly
    return system_prompt, user_prompt


__all__ = [
    "NARRATOR_SYSTEM_PROMPT",
    "NARRATIVE_SYSTEM_PROMPT",
    "build_possession_system_prompt",
    "build_scenario_prompt",
    "build_possession_prompt",
]
