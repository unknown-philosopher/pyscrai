"""
Entity Advisor - AI assistant for entity management in Anvil phase.

Provides contextual help, suggestions, and analysis for entity operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.systems.llm.models import LLMMessage

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.systems.llm.base import LLMProvider


ENTITY_ADVISOR_SYSTEM_PROMPT = """You are an Entity Advisor for PyScrAI|Forge, a worldbuilding toolkit.

Your role is to help users manage entities (actors, locations, polities, events, objects) in their world.

You can:
- Suggest improvements to entity descriptions
- Identify missing or inconsistent information
- Recommend relationships between entities
- Help with entity merging decisions
- Answer questions about entity data

Be concise, helpful, and focused on the entity management task at hand.
When suggesting changes, be specific about what to modify and why."""


class EntityAdvisor(Agent):
    """AI advisor for entity management operations.
    
    Provides intelligent assistance during the Anvil phase,
    helping users refine entities, suggest relationships,
    and maintain consistency.
    
    Usage:
        advisor = EntityAdvisor(llm_provider)
        response = await advisor.suggest_improvements(entity)
    """
    
    def __init__(self, provider: LLMProvider):
        """Initialize the entity advisor.
        
        Args:
            provider: LLM provider for generating responses
        """
        super().__init__(
            role=AgentRole.ADVISOR,
            provider=provider,
            system_prompt=ENTITY_ADVISOR_SYSTEM_PROMPT,
        )
    
    async def suggest_improvements(self, entity: Entity) -> AgentResponse:
        """Suggest improvements for an entity.
        
        Args:
            entity: Entity to analyze
            
        Returns:
            Response with improvement suggestions
        """
        prompt = f"""Analyze this entity and suggest improvements:

Name: {entity.name}
Type: {entity.entity_type.value}
Description: {entity.description or "No description"}
Aliases: {', '.join(entity.aliases) if entity.aliases else 'None'}
Attributes: {entity.attributes}

Suggest:
1. Description improvements (if needed)
2. Missing information that should be added
3. Potential relationships to explore
4. Any inconsistencies to address"""

        return await self._generate(prompt)
    
    async def suggest_relationships(
        self,
        entity: Entity,
        other_entities: list[Entity],
    ) -> AgentResponse:
        """Suggest relationships between entities.
        
        Args:
            entity: Primary entity
            other_entities: Other entities to consider
            
        Returns:
            Response with relationship suggestions
        """
        others_text = "\n".join(
            f"- {e.name} ({e.entity_type.value}): {e.description[:100] if e.description else 'No description'}..."
            for e in other_entities[:10]  # Limit to 10
        )
        
        prompt = f"""Suggest relationships between this entity and others:

Primary Entity:
- Name: {entity.name}
- Type: {entity.entity_type.value}
- Description: {entity.description or "No description"}

Other Entities:
{others_text}

For each suggested relationship, provide:
1. The related entity name
2. Relationship type (e.g., ALLY, ENEMY, MEMBER, LOCATED_IN)
3. Brief justification"""

        return await self._generate(prompt)
    
    async def help_merge_decision(
        self,
        entity_a: Entity,
        entity_b: Entity,
    ) -> AgentResponse:
        """Help decide whether to merge two entities.
        
        Args:
            entity_a: First entity
            entity_b: Second entity
            
        Returns:
            Response with merge recommendation
        """
        prompt = f"""Analyze whether these two entities should be merged:

Entity A:
- Name: {entity_a.name}
- Type: {entity_a.entity_type.value}
- Description: {entity_a.description or "No description"}
- Aliases: {entity_a.aliases}

Entity B:
- Name: {entity_b.name}
- Type: {entity_b.entity_type.value}
- Description: {entity_b.description or "No description"}
- Aliases: {entity_b.aliases}

Provide:
1. Your recommendation (MERGE or KEEP_SEPARATE)
2. Confidence level (HIGH, MEDIUM, LOW)
3. Reasoning for your decision
4. If merging, suggest the merged name and combined description"""

        return await self._generate(prompt)
    
    async def answer_question(
        self,
        question: str,
        context_entities: list[Entity] | None = None,
    ) -> AgentResponse:
        """Answer a question about entities.
        
        Args:
            question: User's question
            context_entities: Relevant entities for context
            
        Returns:
            Response to the question
        """
        context = ""
        if context_entities:
            context = "\n\nRelevant entities:\n" + "\n".join(
                f"- {e.name} ({e.entity_type.value}): {e.description[:100] if e.description else 'No description'}..."
                for e in context_entities[:5]
            )
        
        prompt = f"""User question: {question}{context}

Provide a helpful, concise answer focused on entity management."""

        return await self._generate(prompt)
