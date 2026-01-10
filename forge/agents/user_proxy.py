"""
User Proxy Agent - Intent Router for the Assistant.

This agent acts as the "brain" of the AI Assistant sidebar.
It classifies user input as COMMAND or QUERY and routes accordingly:
- COMMAND → Triggers mutations (create, update, delete entities/relationships)
- QUERY → Routes to phase-specific Advisors for context-aware answers

Uses Few-Shot prompting for reliable intent classification.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forge.agents.base import Agent, AgentResponse, AgentRole
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.systems.llm.base import LLMProvider
    from forge.systems.storage.database import DatabaseManager

logger = get_logger("agents.user_proxy")


# ============================================================================
# Intent Classification
# ============================================================================


class Intent(str, Enum):
    """User intent types."""
    COMMAND = "command"  # Action to perform (create, update, delete)
    QUERY = "query"      # Question to answer


class CommandAction(str, Enum):
    """Supported command actions."""
    CREATE_ENTITY = "create_entity"
    UPDATE_ENTITY = "update_entity"
    DELETE_ENTITY = "delete_entity"
    CREATE_RELATIONSHIP = "create_relationship"
    DELETE_RELATIONSHIP = "delete_relationship"
    MERGE_ENTITIES = "merge_entities"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Parsed user intent with extracted parameters."""
    intent: Intent
    action: CommandAction | None = None
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_response: str = ""


# ============================================================================
# Failure Logging (for prompt iteration)
# ============================================================================


class IntentFailureLogger:
    """Logs failed intent classifications for prompt tuning."""
    
    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or Path("data/logs/intent_failures.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log_failure(
        self,
        user_input: str,
        raw_response: str,
        error: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a failed intent classification."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "raw_response": raw_response,
            "error": error,
            "context": context or {},
        }
        
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log intent failure: {e}")


# ============================================================================
# Few-Shot Prompt Template
# ============================================================================


INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a worldbuilding application.
Classify user input as either a COMMAND (action to perform) or QUERY (question to answer).

## Output Format
Respond with valid JSON only:
{"intent": "command" | "query", "action": "<action_type>", "params": {...}, "confidence": 0.0-1.0}

## Command Actions
- create_entity: Create a new entity
- update_entity: Modify an existing entity
- delete_entity: Remove an entity
- create_relationship: Link two entities
- delete_relationship: Remove a link
- merge_entities: Combine duplicate entities
- unknown: Action not recognized

## Examples

User: "Create a new character named Agent Smith"
{"intent": "command", "action": "create_entity", "params": {"name": "Agent Smith", "entity_type": "ACTOR"}, "confidence": 0.95}

User: "Delete the entity called Abandoned Warehouse"
{"intent": "command", "action": "delete_entity", "params": {"name": "Abandoned Warehouse"}, "confidence": 0.90}

User: "Change Agent Smith's status to MIA"
{"intent": "command", "action": "update_entity", "params": {"name": "Agent Smith", "field": "status", "value": "MIA"}, "confidence": 0.92}

User: "Link Agent Smith to The Organization as a member"
{"intent": "command", "action": "create_relationship", "params": {"source": "Agent Smith", "target": "The Organization", "relationship_type": "member_of"}, "confidence": 0.88}

User: "Merge Agent Smith and John Smith - they're the same person"
{"intent": "command", "action": "merge_entities", "params": {"entity1": "Agent Smith", "entity2": "John Smith"}, "confidence": 0.85}

User: "Who is Agent Smith?"
{"intent": "query", "action": null, "params": {"topic": "Agent Smith"}, "confidence": 0.95}

User: "What relationships does Alice have?"
{"intent": "query", "action": null, "params": {"topic": "Alice", "query_type": "relationships"}, "confidence": 0.90}

User: "Summarize the main factions"
{"intent": "query", "action": null, "params": {"query_type": "summary", "topic": "factions"}, "confidence": 0.88}

User: "Generate a psychological profile for this agent"
{"intent": "query", "action": null, "params": {"query_type": "analysis", "topic": "selected_entity"}, "confidence": 0.85}

## Current Context
Active Page: {active_page}
Selected Entities: {selected_entities}

## User Input
{user_input}

## Response (JSON only)
"""


# ============================================================================
# User Proxy Agent
# ============================================================================


class UserProxyAgent(Agent):
    """Intent router for the AI Assistant.
    
    Classifies user input and routes to appropriate handlers:
    - Commands → DatabaseManager mutations
    - Queries → Phase-specific Advisors
    """
    
    def __init__(
        self,
        llm_provider: "LLMProvider",
        db_manager: "DatabaseManager | None" = None,
    ) -> None:
        super().__init__(
            role=AgentRole.ANALYST,
            llm_provider=llm_provider,
        )
        self.db_manager = db_manager
        self.failure_logger = IntentFailureLogger()
    
    async def process(
        self,
        user_input: str,
        active_page: str = "dashboard",
        selected_entities: list["Entity"] | None = None,
    ) -> AgentResponse:
        """Process user input and return appropriate response.
        
        Args:
            user_input: Raw text from the user
            active_page: Current UI page (e.g., 'osint', 'humint')
            selected_entities: Currently selected entities in the UI
            
        Returns:
            AgentResponse with message and optional action taken
        """
        selected_entities = selected_entities or []
        
        # Step 1: Classify intent
        parsed = await self._classify_intent(
            user_input,
            active_page,
            selected_entities,
        )
        
        # Step 2: Route based on intent
        if parsed.intent == Intent.COMMAND:
            return await self._handle_command(parsed, selected_entities)
        else:
            return await self._handle_query(parsed, active_page, selected_entities)
    
    async def _classify_intent(
        self,
        user_input: str,
        active_page: str,
        selected_entities: list["Entity"],
    ) -> ParsedIntent:
        """Classify the user's intent using LLM."""
        # Format selected entities for context
        entity_names = [e.name for e in selected_entities[:5]]  # Limit for context
        selected_str = ", ".join(entity_names) if entity_names else "None"
        
        # Build prompt
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            active_page=active_page,
            selected_entities=selected_str,
            user_input=user_input,
        )
        
        try:
            # Call LLM
            from forge.systems.llm.models import LLMMessage, MessageRole
            
            messages = [
                LLMMessage(role=MessageRole.SYSTEM, content="You are a precise JSON classifier."),
                LLMMessage(role=MessageRole.USER, content=prompt),
            ]
            
            response = await self.llm_provider.generate(messages)
            raw_response = response.content.strip()
            
            # Parse JSON response
            return self._parse_intent_response(raw_response, user_input)
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            self.failure_logger.log_failure(
                user_input=user_input,
                raw_response="",
                error=str(e),
                context={"active_page": active_page},
            )
            
            # Default to query on failure
            return ParsedIntent(
                intent=Intent.QUERY,
                confidence=0.0,
                raw_response="",
            )
    
    def _parse_intent_response(self, raw_response: str, user_input: str) -> ParsedIntent:
        """Parse the LLM's JSON response into a ParsedIntent."""
        try:
            # Clean up response (remove markdown code blocks if present)
            clean = raw_response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1]  # Remove first line
                clean = clean.rsplit("```", 1)[0]  # Remove last line
            clean = clean.strip()
            
            data = json.loads(clean)
            
            intent = Intent(data.get("intent", "query"))
            action = None
            if data.get("action"):
                try:
                    action = CommandAction(data["action"])
                except ValueError:
                    action = CommandAction.UNKNOWN
            
            return ParsedIntent(
                intent=intent,
                action=action,
                params=data.get("params", {}),
                confidence=float(data.get("confidence", 0.5)),
                raw_response=raw_response,
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse intent response: {e}")
            self.failure_logger.log_failure(
                user_input=user_input,
                raw_response=raw_response,
                error=str(e),
            )
            
            # Default to query
            return ParsedIntent(
                intent=Intent.QUERY,
                confidence=0.0,
                raw_response=raw_response,
            )
    
    async def _handle_command(
        self,
        parsed: ParsedIntent,
        selected_entities: list["Entity"],
    ) -> AgentResponse:
        """Execute a command action."""
        if not self.db_manager:
            return AgentResponse(
                message="⚠️ Database not available. Cannot execute commands.",
                success=False,
            )
        
        action = parsed.action
        params = parsed.params
        
        try:
            if action == CommandAction.CREATE_ENTITY:
                return await self._create_entity(params)
            
            elif action == CommandAction.UPDATE_ENTITY:
                return await self._update_entity(params, selected_entities)
            
            elif action == CommandAction.DELETE_ENTITY:
                return await self._delete_entity(params, selected_entities)
            
            elif action == CommandAction.CREATE_RELATIONSHIP:
                return await self._create_relationship(params)
            
            elif action == CommandAction.DELETE_RELATIONSHIP:
                return await self._delete_relationship(params)
            
            elif action == CommandAction.MERGE_ENTITIES:
                return await self._merge_entities(params)
            
            else:
                return AgentResponse(
                    message=f"❓ I understood this as a command, but I'm not sure how to handle: {action}",
                    success=False,
                )
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return AgentResponse(
                message=f"❌ Command failed: {str(e)}",
                success=False,
            )
    
    async def _handle_query(
        self,
        parsed: ParsedIntent,
        active_page: str,
        selected_entities: list["Entity"],
    ) -> AgentResponse:
        """Route a query to the appropriate advisor."""
        # Map pages to advisors
        advisor_map = {
            "osint": "OsintAdvisor",
            "humint": "HumintAdvisor",
            "sigint": "SigintAdvisor",
            "synth": "SynthAdvisor",
            "geoint": "GeointAdvisor",
            "anvil": "AnvilAdvisor",
        }
        
        advisor_name = advisor_map.get(active_page, "OsintAdvisor")
        
        try:
            # Dynamically load advisor
            advisor = await self._get_advisor(advisor_name)
            
            if advisor:
                # Build context
                context = {
                    "query": parsed.params.get("topic", ""),
                    "query_type": parsed.params.get("query_type", "general"),
                    "selected_entities": selected_entities,
                }
                
                response = await advisor.advise(context)
                return AgentResponse(
                    message=response.message,
                    success=True,
                    data=response.data,
                )
            else:
                # Fallback: Use general LLM response
                return await self._general_query(parsed)
                
        except Exception as e:
            logger.error(f"Query handling failed: {e}")
            return await self._general_query(parsed)
    
    async def _get_advisor(self, advisor_name: str):
        """Get an advisor instance by name."""
        try:
            module_name = advisor_name.lower().replace("advisor", "_advisor")
            module = __import__(
                f"forge.agents.advisors.{module_name}",
                fromlist=[advisor_name],
            )
            advisor_class = getattr(module, advisor_name)
            return advisor_class(llm_provider=self.llm_provider)
        except (ImportError, AttributeError) as e:
            logger.debug(f"Advisor {advisor_name} not available: {e}")
            return None
    
    async def _general_query(self, parsed: ParsedIntent) -> AgentResponse:
        """Handle query with general LLM response."""
        topic = parsed.params.get("topic", "your question")
        
        from forge.systems.llm.models import LLMMessage, MessageRole
        
        messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="You are a helpful worldbuilding assistant for a narrative intelligence application.",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content=f"Answer this question about the world: {topic}",
            ),
        ]
        
        response = await self.llm_provider.generate(messages)
        
        return AgentResponse(
            message=response.content,
            success=True,
        )
    
    # ========== Command Implementations ==========
    
    async def _create_entity(self, params: dict) -> AgentResponse:
        """Create a new entity."""
        from forge.core.models.entity import EntityType, create_entity
        
        name = params.get("name")
        entity_type_str = params.get("entity_type", "ACTOR")
        
        if not name:
            return AgentResponse(
                message="❌ Please specify a name for the entity.",
                success=False,
            )
        
        try:
            entity_type = EntityType(entity_type_str.upper())
        except ValueError:
            entity_type = EntityType.ACTOR
        
        entity = create_entity(
            entity_type=entity_type,
            name=name,
            description=params.get("description", ""),
        )
        
        self.db_manager.save_entity(entity)
        
        return AgentResponse(
            message=f"✅ Created entity: **{entity.name}** ({entity_type.value})",
            success=True,
            action_taken=f"Created {entity.id}",
            data={"entity_id": entity.id},
        )
    
    async def _update_entity(
        self,
        params: dict,
        selected_entities: list["Entity"],
    ) -> AgentResponse:
        """Update an existing entity."""
        name = params.get("name")
        field = params.get("field")
        value = params.get("value")
        
        # Find entity
        entity = None
        if name:
            entities = self.db_manager.search_entities(name)
            entity = entities[0] if entities else None
        elif selected_entities:
            entity = selected_entities[0]
        
        if not entity:
            return AgentResponse(
                message=f"❌ Could not find entity: {name or 'selected'}",
                success=False,
            )
        
        if not field or value is None:
            return AgentResponse(
                message="❌ Please specify what field to update and the new value.",
                success=False,
            )
        
        # Update field
        if hasattr(entity, field):
            setattr(entity, field, value)
        else:
            entity.attributes[field] = value
        
        self.db_manager.save_entity(entity)
        
        return AgentResponse(
            message=f"✅ Updated **{entity.name}**: {field} → {value}",
            success=True,
            action_taken=f"Updated {entity.id}.{field}",
        )
    
    async def _delete_entity(
        self,
        params: dict,
        selected_entities: list["Entity"],
    ) -> AgentResponse:
        """Delete an entity."""
        name = params.get("name")
        
        # Find entity
        entity = None
        if name:
            entities = self.db_manager.search_entities(name)
            entity = entities[0] if entities else None
        elif selected_entities:
            entity = selected_entities[0]
        
        if not entity:
            return AgentResponse(
                message=f"❌ Could not find entity: {name or 'selected'}",
                success=False,
            )
        
        entity_name = entity.name
        self.db_manager.delete_entity(entity.id)
        
        return AgentResponse(
            message=f"🗑️ Deleted entity: **{entity_name}**",
            success=True,
            action_taken=f"Deleted {entity.id}",
        )
    
    async def _create_relationship(self, params: dict) -> AgentResponse:
        """Create a relationship between entities."""
        from forge.core.models.relationship import RelationType, create_relationship
        
        source_name = params.get("source")
        target_name = params.get("target")
        rel_type_str = params.get("relationship_type", "RELATED_TO")
        
        if not source_name or not target_name:
            return AgentResponse(
                message="❌ Please specify both source and target entities.",
                success=False,
            )
        
        # Find entities
        source_results = self.db_manager.search_entities(source_name)
        target_results = self.db_manager.search_entities(target_name)
        
        if not source_results:
            return AgentResponse(
                message=f"❌ Could not find source entity: {source_name}",
                success=False,
            )
        if not target_results:
            return AgentResponse(
                message=f"❌ Could not find target entity: {target_name}",
                success=False,
            )
        
        source = source_results[0]
        target = target_results[0]
        
        try:
            rel_type = RelationType(rel_type_str.upper())
        except ValueError:
            rel_type = RelationType.RELATED_TO
        
        relationship = create_relationship(
            source_id=source.id,
            target_id=target.id,
            relationship_type=rel_type,
            label=f"{source.name} → {target.name}",
        )
        
        self.db_manager.save_relationship(relationship)
        
        return AgentResponse(
            message=f"🔗 Created relationship: **{source.name}** → **{target.name}** ({rel_type.value})",
            success=True,
            action_taken=f"Created {relationship.id}",
        )
    
    async def _delete_relationship(self, params: dict) -> AgentResponse:
        """Delete a relationship."""
        # This would need more context to identify the specific relationship
        return AgentResponse(
            message="⚠️ Relationship deletion requires selecting the specific relationship in the UI.",
            success=False,
        )
    
    async def _merge_entities(self, params: dict) -> AgentResponse:
        """Merge two entities."""
        entity1_name = params.get("entity1")
        entity2_name = params.get("entity2")
        
        if not entity1_name or not entity2_name:
            return AgentResponse(
                message="❌ Please specify both entities to merge.",
                success=False,
            )
        
        # Find entities
        results1 = self.db_manager.search_entities(entity1_name)
        results2 = self.db_manager.search_entities(entity2_name)
        
        if not results1 or not results2:
            return AgentResponse(
                message="❌ Could not find one or both entities.",
                success=False,
            )
        
        # Delegate to merger
        from forge.phases.p5_finalize.merger import EntityMerger
        
        merger = EntityMerger(self.db_manager)
        merged = merger.merge(results1[0], results2[0])
        
        return AgentResponse(
            message=f"🔀 Merged entities into: **{merged.name}**",
            success=True,
            action_taken=f"Merged into {merged.id}",
        )
