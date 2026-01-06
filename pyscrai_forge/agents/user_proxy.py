"""UserProxyAgent: Natural language interface for data manipulation.

This agent interprets user requests and executes operations directly on
the project database or JSON files, allowing conversational refinement
of extracted entities and relationships.
"""

import json
import re
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from pathlib import Path

from pyscrai_core import Entity, Relationship, RelationshipType

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider
    from pyscrai_forge.src import storage


class UserProxyAgent:
    """Interprets natural language commands and manipulates project data.
    
    Capabilities:
    - Merge entities: "Merge entity A into entity B"
    - Split entities: "Split entity A into A1 and A2"
    - Add relationships: "Create a relationship between A and B"
    - Remove entities: "Delete entity A"
    - Modify entity properties: "Change entity A's description to..."
    - List/filter: "Show me all actors"
    - Direct JSON/SQL editing: "Update the bio field for entity X to..."
    """

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
    
    async def process_command(self, user_input: str, entities: List[Entity], relationships: List[Relationship]) -> Dict[str, Any] | str:
        """Process user input and execute appropriate operations.
        
        Args:
            user_input: Natural language command from user
            entities: Current list of entities
            relationships: Current list of relationships
            
        Returns:
            Response message describing what was done
        """
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Build context about current entities
        entity_list = "\n".join([
            f"- {e.descriptor.name} ({e.descriptor.entity_type.value}) [ID: {e.id}]"
            for e in entities
        ])
        
        relationship_list = "\n".join([
            f"- {r.source_id} --{r.relationship_type.value}--> {r.target_id}"
            for r in relationships
        ])
        
        system_prompt = f"""You are a helpful assistant that helps users refine extracted entity data.
You have access to the following entities and relationships:

ENTITIES:
{entity_list}

RELATIONSHIPS:
{relationship_list}

Respond with ONE JSON object only. No prose, no bullet lists, no code fences.

Schema:
{{
    "operation": "merge" | "split" | "add_relationship" | "remove_entity" | "modify_entity" | "batch_modify" | "help" | "list",
    "entities_involved": ["entity_id_1", "entity_id_2"],
    "details": {{}},
    "message": "Human-readable description of what will happen"
}}

Merge example:
{{
    "operation": "merge",
    "entities_involved": ["keep_id", "merge_id"],
    "details": {{"keep_id": "id_to_keep", "merge_id": "id_to_merge"}},
    "message": "Merging entity merge_id into keep_id"
}}

Split example:
{{
    "operation": "split",
    "entities_involved": ["entity_id"],
    "details": {{"entity_id": "original_id", "split_into": ["new_entity_1", "new_entity_2"]}},
    "message": "Splitting entity_id into new entities"
}}

Relationship example:
{{
    "operation": "add_relationship",
    "entities_involved": ["source_id", "target_id"],
    "details": {{"source_id": "...", "target_id": "...", "type": "supports|conflicts|related_to|custom"}},
    "message": "Creating relationship between source and target"
}}

Removal example:
{{
    "operation": "remove_entity",
    "entities_involved": ["entity_id"],
    "details": {{"entity_id": "..."}},
    "message": "Removing entity_id from project"
}}

Single modify example:
{{
    "operation": "modify_entity",
    "entities_involved": ["entity_id"],
    "details": {{"entity_id": "...", "field": "bio|name|description|health|wealth|custom_field", "value": "new_value"}},
    "message": "Updating entity_id field to new_value"
}}

Batch modify example (use when multiple entities or fields are updated in one request):
{{
    "operation": "batch_modify",
    "entities_involved": ["entity_id_1", "entity_id_2"],
    "details": {{"updates": [
        {{"entity_id": "entity_id_1", "field": "health", "value": 100}},
        {{"entity_id": "entity_id_2", "field": "wealth", "value": 500}}
    ]}},
    "message": "Updating fields for listed entities"
}}

List example:
{{
    "operation": "list",
    "entities_involved": [],
    "details": {{"filter": "all|actors|locations|etc"}},
    "message": "Showing entities matching filter"
}}

Help example:
{{
    "operation": "help",
    "entities_involved": [],
    "details": {{}},
    "message": "Here are the things you can ask me to do..."
}}
"""
        
        try:
            response = await self.provider.complete_simple(
                prompt=user_input,
                system_prompt=system_prompt,
                temperature=0.2,
                model=self.model or self.provider.default_model
            )

            operation_data = self._extract_json_object(response)
            if not operation_data:
                msg = (
                    "I didn't understand that. Could you rephrase with a clear action? "
                    "(Example: 'Merge entity A into entity B' or 'Set health=100 for ENTITY_006')"
                )
                self.conversation_history.append({"role": "assistant", "content": msg})
                return {"operation": "error", "message": msg}

            self.conversation_history.append({"role": "assistant", "content": response})
            return operation_data

        except json.JSONDecodeError as e:
            error_msg = f"I tried to process that but got confused. Could you rephrase? (Error: {str(e)[:80]})"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return {"operation": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return {"operation": "error", "message": error_msg}
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def _extract_json_object(self, response: str) -> Optional[Dict[str, Any]]:
        """Robustly extract the first JSON object from an LLM response.

        Accepts raw text, optional code fences, and trailing notes. Uses
        JSONDecoder.raw_decode to safely ignore trailing content after the
        first valid object.
        """

        if not response:
            return None

        cleaned = response.strip()

        fence_match = re.search(r"```json\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if not fence_match:
            fence_match = re.search(r"```\s*(\{.*?\})\s*```", cleaned, re.DOTALL)

        if fence_match:
            candidate = fence_match.group(1)
        else:
            brace_index = cleaned.find("{")
            if brace_index == -1:
                return None
            candidate = cleaned[brace_index:]

        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(candidate)
            return obj
        except json.JSONDecodeError:
            # Try a non-greedy brace match as a fallback
            fallback_match = re.search(r"\{.*?\}", candidate, re.DOTALL)
            if not fallback_match:
                return None
            try:
                obj, _ = decoder.raw_decode(fallback_match.group(0))
                return obj
            except json.JSONDecodeError:
                return None
