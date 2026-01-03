"""Analysis prompts for the Analyst Agent.

The Analyst Agent handles both entity extraction and data refinement.
This module provides prompts for both capabilities.
"""

import json
from typing import Dict, Any
from .core import BASE_SYSTEM_PROMPT, Genre

# =============================================================================
# ANALYST SYSTEM PROMPT
# =============================================================================

ANALYST_SYSTEM_PROMPT = f"""{BASE_SYSTEM_PROMPT}

You are THE ANALYST, the data extraction and refinement agent of PyScrAI|Forge.

ROLE: DATA SCIENTIST
--------------------
You are responsible for two key tasks:
1. EXTRACTION: Extract entities and their quantitative stats from raw text
2. REFINEMENT: Clean, structure, and validate JSON data according to project schemas

CAPABILITIES:
- Entity Discovery: Identify all significant entities in text (polity, actor, location, abstract)
- Schema-Based Extraction: Extract quantitative values defined in Project Schema
- Data Refinement: Clean duplicates, fix inconsistencies, validate relationships
- Schema Compliance: Ensure all data strictly follows Project Manifest schemas
"""

# =============================================================================
# EXTRACTION PROMPTS (from harvester_prompts.py)
# =============================================================================

SYSTEM_PROMPT_ANALYST_EXTRACTION = """You are the Analyst, a data mining agent.
Your Goal: Fill in the stat sheets for specific entities using the Project Schema.

EXTRACTION FOCUS:
You are in "Analysis Mode". You will be given a specific entity to analyze and the Project Schema.
Your job is to read the text and extract specific quantitative values defined in the schema.

CRITICAL RULES:
1. SCHEMA AWARENESS: Look ONLY for the fields defined in the schema provided.
   - If schema asks for "health" and "gold", look for those.
   - Ignore other stats not in the schema.

2. NO HALLUCINATIONS: 
   - If the text does not state the value, return null.
   - Do NOT guess. Do NOT estimate. 

3. OUTPUT FORMAT: JSON object with "resources" key containing the extracted values.
"""

ANALYST_EXTRACTION_EXAMPLE = """
SCHEMA:
{
  "health": "float (0-100)",
  "gold": "int"
}

TEXT:
"The hero had 50 gold coins but was wounded, leaving him with half his vitality."

OUTPUT:
{
  "resources": {
    "health": 50.0,
    "gold": 50
  }
}
"""

# =============================================================================
# REFINEMENT PROMPTS (from architect_prompts.py JSON_REFINER_PROMPT)
# =============================================================================

JSON_REFINER_PROMPT = f"""{BASE_SYSTEM_PROMPT}

You are THE REFINER, the JSON refinement component of the Analyst Agent.

TASKS:
1. CLEANING: Remove duplicates, fix naming inconsistencies, and resolve conflicting IDs.
2. STRUCTURING: Ensure the data strictly follows the Project Manifest schemas.
3. SUMMARIZATION: Add a "forge_summary" field to each entity explaining its role in the project.
4. RELATIONSHIP MAPPING: Verify that all referenced IDs in 'relationships' actually exist.

OUTPUT:
Provide ONLY the valid, enhanced JSON object. No narrative text.
"""

# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def build_extraction_prompt(
    text: str,
    entity_name: str,
    entity_type: str,
    schema: dict[str, str],
    description: str = ""
) -> tuple[str, str]:
    """Build prompts for Analyst extraction phase.
    
    Args:
        text: Source text to analyze
        entity_name: Name of the entity to extract
        entity_type: Type of entity (polity, actor, location, etc.)
        schema: Project schema defining fields to extract
        description: Optional description of the entity
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_parts = [SYSTEM_PROMPT_ANALYST_EXTRACTION]
    system_parts.append("\nEXAMPLE:\n" + ANALYST_EXTRACTION_EXAMPLE)
    
    system_prompt = "\n".join(system_parts)
    
    schema_str = json.dumps(schema, indent=2)
    
    user_prompt = f"""Analyze the text for this specific entity.
    
ENTITY: {entity_name} ({entity_type})
DESCRIPTION: {description}

PROJECT SCHEMA (Look for these fields):
{schema_str}

TEXT:
---
{text}
---

JSON OUTPUT:"""
    return system_prompt, user_prompt


def build_refinement_prompt(
    raw_data: Dict[str, Any],
    schema_context: Dict[str, Any]
) -> tuple[str, str]:
    """Build prompts for Analyst refinement phase.
    
    Args:
        raw_data: Raw JSON data to refine
        schema_context: Project schema and context for validation
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = JSON_REFINER_PROMPT
    
    user_prompt = f"""SCHEMA CONTEXT:
{json.dumps(schema_context, indent=2)}

RAW DATA:
{json.dumps(raw_data, indent=2)}

Refine and structure this data according to the schema. Output ONLY the enhanced JSON object."""
    
    return system_prompt, user_prompt


__all__ = [
    "ANALYST_SYSTEM_PROMPT",
    "SYSTEM_PROMPT_ANALYST_EXTRACTION",
    "JSON_REFINER_PROMPT",
    "build_extraction_prompt",
    "build_refinement_prompt",
]
