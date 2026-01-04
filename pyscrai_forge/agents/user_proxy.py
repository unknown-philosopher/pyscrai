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
    
    async def process_command(self, user_input: str, entities: List[Entity], relationships: List[Relationship]) -> str:
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

When the user asks you to modify entities or relationships, respond with a JSON object describing the operation.
Respond ONLY with valid JSON in this format:

{{
    "operation": "merge" | "split" | "add_relationship" | "remove_entity" | "modify_entity" | "help" | "list",
    "entities_involved": ["entity_id_1", "entity_id_2"],
    "details": {{}},
    "message": "Human-readable description of what will happen"
}}

For merge operations:
{{
    "operation": "merge",
    "entities_involved": ["keep_id", "merge_id"],
    "details": {{"keep_id": "id_to_keep", "merge_id": "id_to_merge"}},
    "message": "Merging entity merge_id into keep_id"
}}

For split operations:
{{
    "operation": "split",
    "entities_involved": ["entity_id"],
    "details": {{"entity_id": "original_id", "split_into": ["new_entity_1", "new_entity_2"]}},
    "message": "Splitting entity_id into new entities"
}}

For relationship operations:
{{
    "operation": "add_relationship",
    "entities_involved": ["source_id", "target_id"],
    "details": {{"source_id": "...", "target_id": "...", "type": "supports|conflicts|related_to|custom"}},
    "message": "Creating relationship between source and target"
}}

For entity removal:
{{
    "operation": "remove_entity",
    "entities_involved": ["entity_id"],
    "details": {{"entity_id": "..."}},
    "message": "Removing entity_id from project"
}}

For entity modifications:
{{
    "operation": "modify_entity",
    "entities_involved": ["entity_id"],
    "details": {{"entity_id": "...", "field": "bio|name|description", "value": "new_value"}},
    "message": "Updating entity_id field to new_value"
}}

For listing/filtering:
{{
    "operation": "list",
    "entities_involved": [],
    "details": {{"filter": "all|actors|locations|etc"}},
    "message": "Showing entities matching filter"
}}

For help:
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
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return f"I didn't understand that. Could you be more specific? (Example: 'Merge entity A into entity B' or 'Add a relationship between A and B')"
            
            operation_data = json.loads(json_match.group())
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return operation_data
            
        except json.JSONDecodeError as e:
            error_msg = f"I tried to process that but got confused. Could you rephrase? (Error: {str(e)[:50]})"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return {"operation": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return {"operation": "error", "message": error_msg}
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
