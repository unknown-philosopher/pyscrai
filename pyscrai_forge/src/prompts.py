"""Prompt templates for LLM entity extraction.

The Harvester uses carefully engineered prompts to extract structured
JSON from raw text. These prompts are genre-aware and map directly
to the pyscrai_core ECS model.

Prompt Engineering Principles:
1. Explicit JSON schema in the prompt
2. Few-shot examples for each entity type
3. Genre-specific terminology guidance
4. Strict instruction to output ONLY valid JSON
"""

from dataclasses import dataclass
from enum import Enum
import json


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
# SYSTEM PROMPTS - SCOUT (ENTITY DISCOVERY)
# =============================================================================

SYSTEM_PROMPT_SCOUT = """You are the Scout, an entity discovery agent.
Your Goal: Identify all potential entities in the text.

EXTRACTION FOCUS:
You are in "Discovery Mode". Your ONLY job is to find and list entities.
DO NOT extract stats, numbers, or details yet. Just identify WHO/WHAT they are.

CRITICAL RULES:
1. HIGH RECALL: Capture every significant entity mentioned.
   - "polity" (Nations, Factions, Families, Corps, Orgs)
   - "actor" (Individuals, Characters, Leaders)
   - "location" (Cities, Regions, Places, Territories)
   - "abstract" (Concepts, Treaties, Events - use sparingly)

2. EXTRACT "SILENT" LOCATIONS: 
   - Extract locations even if they have no description. "He traveled to Sicily" -> Location: "Sicily".

3. OUTPUT FORMAT: Output ONLY the JSON object with an "entities" list. 
   - ID: Create a unique ID (e.g., ent_name_001)
   - Type: polity, actor, location, or abstract
   - Name: Common name
   - Description: Brief one-line summary
"""

SCOUT_SCHEMA = """
{
  "entities": [
    {
      "id": "ent_unique_id_001",
      "entity_type": "polity|actor|location|abstract",
      "name": "Entity Name",
      "aliases": ["Alias1", "Alias2"],
      "description": "Brief summary",
      "tags": ["tag1", "tag2"]
    }
  ]
}
"""

SCOUT_EXAMPLE = """
INPUT TEXT:
"In 264 BC, Rome declared war on Carthage over control of Sicily. The Roman Republic, led by Consul Appius Claudius..."

OUTPUT:
{
  "entities": [
    {
      "id": "ent_rome_001",
      "entity_type": "polity",
      "name": "Roman Republic",
      "aliases": ["Rome"],
      "description": "Ancient republic that declared war on Carthage",
      "tags": ["republic"]
    },
    {
      "id": "ent_carthage_001",
      "entity_type": "polity",
      "name": "Carthage",
      "aliases": [],
      "description": "Rival power to Rome",
      "tags": ["enemy"]
    },
    {
      "id": "ent_sicily_001",
      "entity_type": "location",
      "name": "Sicily",
      "aliases": [],
      "description": "Mediterranean island",
      "tags": ["island"]
    },
    {
      "id": "ent_claudius_001",
      "entity_type": "actor",
      "name": "Appius Claudius",
      "aliases": ["Consul Appius Claudius"],
      "description": "Roman Consul",
      "tags": ["consul", "roman"]
    }
  ]
}
"""

# =============================================================================
# SYSTEM PROMPTS - ANALYST (DATA MINING)
# =============================================================================

SYSTEM_PROMPT_ANALYST = """You are the Analyst, a data mining agent.
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

ANALYST_EXAMPLE = """
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
# SYSTEM PROMPTS - RELATIONSHIPS
# =============================================================================

SYSTEM_PROMPT_RELATIONSHIPS = """You are the Harvester, a strict database extraction agent.
Your Goal: Identify relationships between provided entities based on the text.

EXTRACTION FOCUS:
You are in "Relationship Discovery Mode". You will be given a list of EXISTING entities and a text.
Your job is to find how these specific entities are related in the text.
DO NOT create new entities. Use the exact IDs provided.

CRITICAL RULES:
1. STRICT REFERENTIAL INTEGRITY:
   - You may ONLY use the "id" values from the provided Entity List.
   - If the text mentions a relationship involving an entity NOT in the list, SKIP IT.
   - source_id and target_id MUST match one of the provided IDs exactly.

2. RELATIONSHIP TYPES:
   - ALLIANCE (Friendly, cooperating, peace treaties)
   - RIVALRY (War, enemies, competition, opposing sides)
   - SUBORDINATE (Subject of, vassal of, controlled by)
   - MEMBERSHIP (Member of, citizen of, employee of, family member of)
   - LOCATED_IN (City in region, building in city, person in place)
   - KINSHIP (Family relation, parent/child, sibling)
   - TRADE (Commercial ties)
   - CUSTOM (Anything else)

3. NO HALLUCINATIONS: Do not guess strength or nature. Infer it strictly from the text.

4. OUTPUT FORMAT: Output ONLY the JSON object with a "relationships" list. No "entities" key. No markdown.
"""

RELATIONSHIP_SCHEMA = """
{
  "relationships": [
    {
      "id": "rel_<uuid>",
      "source_id": "ent_<source>",
      "target_id": "ent_<target>",
      "relationship_type": "alliance|rivalry|subordinate|member_of|occupies|kinship|trade|custom",
      "strength": 0.8,
      "description": "Nature of relationship"
    }
  ]
}
"""

# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def get_scout_prompt(text: str, genre: Genre = Genre.GENERIC) -> tuple[str, str]:
    """Build prompts for Scout (Discovery) phase."""
    system_parts = [SYSTEM_PROMPT_SCOUT]
    system_parts.append("\nJSON SCHEMA:\n" + SCOUT_SCHEMA)
    system_parts.append("\nEXAMPLE:\n" + SCOUT_EXAMPLE)
    
    system_prompt = "\n".join(system_parts)
    
    user_prompt = f"""Identify ALL entities in this text.
Output ONLY the JSON object with the "entities" list.

TEXT:
---
{text}
---

JSON OUTPUT:"""
    return system_prompt, user_prompt


def get_analyst_prompt(
    text: str,
    entity_name: str,
    entity_type: str,
    schema: dict[str, str],
    description: str = ""
) -> tuple[str, str]:
    """Build prompts for Analyst (Extraction) phase."""
    system_parts = [SYSTEM_PROMPT_ANALYST]
    system_parts.append("\nEXAMPLE:\n" + ANALYST_EXAMPLE)
    
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


def get_relationship_prompt(
    text: str,
    entities: list[dict],
    genre: Genre = Genre.GENERIC
) -> tuple[str, str]:
    """Build prompts for Relationship phase."""
    system_parts = [SYSTEM_PROMPT_RELATIONSHIPS]
    system_parts.append("\nJSON SCHEMA:\n" + RELATIONSHIP_SCHEMA)
    
    system_prompt = "\n".join(system_parts)
    
    # Simplify entity list
    simplified_entities = [
        {
            "id": e.get("id"),
            "name": e.get("name"), 
            "type": e.get("entity_type"),
            "desc": (e.get("description", "") or "")[:50]
        }
        for e in entities
    ]
    
    user_prompt = f"""Analyze the text and extract relationships between these entities.

PROVIDED ENTITIES (Use these IDs exactly):
{json.dumps(simplified_entities, indent=2)}

TEXT:
---
{text}
---

JSON OUTPUT:"""
    return system_prompt, user_prompt
