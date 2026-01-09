"""
Relationship Advisor - AI assistant for relationship management.

Provides contextual help for creating, analyzing, and managing
relationships between entities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship
    from forge.systems.llm.base import LLMProvider


RELATIONSHIP_ADVISOR_SYSTEM_PROMPT = """You are a Relationship Advisor for PyScrAI|Forge, a worldbuilding toolkit.

Your role is to help users manage relationships between entities in their world.

You can:
- Suggest relationship types and strengths
- Identify missing or implicit relationships
- Analyze relationship networks and patterns
- Help resolve conflicting relationships
- Explain relationship dynamics

Be concise and focused on relationship management.
Consider relationship directionality, strength, and narrative implications."""


class RelationshipAdvisor(Agent):
    """AI advisor for relationship management operations.
    
    Provides intelligent assistance for creating and managing
    relationships between entities in the world.
    
    Usage:
        advisor = RelationshipAdvisor(llm_provider)
        response = await advisor.suggest_type(source, target)
    """
    
    def __init__(self, provider: LLMProvider):
        """Initialize the relationship advisor.
        
        Args:
            provider: LLM provider for generating responses
        """
        super().__init__(
            role=AgentRole.ADVISOR,
            provider=provider,
            system_prompt=RELATIONSHIP_ADVISOR_SYSTEM_PROMPT,
        )
    
    async def suggest_relationship_type(
        self,
        source: Entity,
        target: Entity,
    ) -> AgentResponse:
        """Suggest relationship type between two entities.
        
        Args:
            source: Source entity
            target: Target entity
            
        Returns:
            Response with relationship suggestions
        """
        prompt = f"""Suggest a relationship between these entities:

Source Entity:
- Name: {source.name}
- Type: {source.entity_type.value}
- Description: {source.description or "No description"}

Target Entity:
- Name: {target.name}
- Type: {target.entity_type.value}
- Description: {target.description or "No description"}

Available relationship types:
ALLY, ENEMY, NEUTRAL, MEMBER, LEADER, LOCATED_IN, OWNS, WORKS_FOR, 
REPORTS_TO, PARENT, CHILD, SIBLING, SPOUSE, FRIEND, RIVAL, MENTOR, 
STUDENT, CREATED, DESTROYED, PARTICIPATED, WITNESSED, CUSTOM

Provide:
1. Recommended relationship type
2. Suggested strength (-1.0 to 1.0, where negative means adversarial)
3. Brief description of the relationship
4. Whether it should be bidirectional"""

        return await self._generate(prompt)
    
    async def analyze_relationship(
        self,
        relationship: Relationship,
        source: Entity,
        target: Entity,
    ) -> AgentResponse:
        """Analyze an existing relationship.
        
        Args:
            relationship: Relationship to analyze
            source: Source entity
            target: Target entity
            
        Returns:
            Analysis response
        """
        prompt = f"""Analyze this relationship:

Relationship:
- Type: {relationship.relationship_type.value}
- Strength: {relationship.strength}
- Description: {relationship.description or "No description"}

Source: {source.name} ({source.entity_type.value})
Target: {target.name} ({target.entity_type.value})

Provide:
1. Assessment of the relationship's narrative importance
2. Potential story implications
3. Suggested related relationships to explore
4. Any inconsistencies or concerns"""

        return await self._generate(prompt)
    
    async def find_missing_relationships(
        self,
        entity: Entity,
        existing_relationships: list[tuple[Relationship, Entity]],
        other_entities: list[Entity],
    ) -> AgentResponse:
        """Identify potentially missing relationships.
        
        Args:
            entity: Entity to analyze
            existing_relationships: Current relationships with their targets
            other_entities: Other entities in the world
            
        Returns:
            Response with missing relationship suggestions
        """
        existing_text = "\n".join(
            f"- {rel.relationship_type.value} -> {target.name}"
            for rel, target in existing_relationships[:10]
        ) or "None"
        
        others_text = "\n".join(
            f"- {e.name} ({e.entity_type.value})"
            for e in other_entities[:15]
        )
        
        prompt = f"""Identify missing relationships for this entity:

Entity: {entity.name} ({entity.entity_type.value})
Description: {entity.description or "No description"}

Existing Relationships:
{existing_text}

Other Entities in World:
{others_text}

Based on the entity's description and type, suggest relationships
that are likely missing. For each suggestion, provide:
1. Target entity name
2. Relationship type
3. Why this relationship likely exists"""

        return await self._generate(prompt)
    
    async def resolve_conflict(
        self,
        relationship_a: Relationship,
        relationship_b: Relationship,
        entities: dict[str, Entity],
    ) -> AgentResponse:
        """Help resolve conflicting relationships.
        
        Args:
            relationship_a: First relationship
            relationship_b: Second (conflicting) relationship
            entities: Map of entity IDs to entities
            
        Returns:
            Resolution recommendation
        """
        source_a = entities.get(relationship_a.source_id)
        target_a = entities.get(relationship_a.target_id)
        source_b = entities.get(relationship_b.source_id)
        target_b = entities.get(relationship_b.target_id)
        
        prompt = f"""Help resolve these potentially conflicting relationships:

Relationship A:
- {source_a.name if source_a else 'Unknown'} -> {target_a.name if target_a else 'Unknown'}
- Type: {relationship_a.relationship_type.value}
- Strength: {relationship_a.strength}

Relationship B:
- {source_b.name if source_b else 'Unknown'} -> {target_b.name if target_b else 'Unknown'}
- Type: {relationship_b.relationship_type.value}
- Strength: {relationship_b.strength}

Provide:
1. Whether these are truly conflicting
2. If so, which should take precedence
3. Alternative interpretation that resolves the conflict
4. Recommended action (keep both, merge, delete one)"""

        return await self._generate(prompt)
    
    async def answer_question(
        self,
        question: str,
        context_relationships: list[tuple[Relationship, Entity, Entity]] | None = None,
    ) -> AgentResponse:
        """Answer a question about relationships.
        
        Args:
            question: User's question
            context_relationships: Relevant relationships with their entities
            
        Returns:
            Response to the question
        """
        context = ""
        if context_relationships:
            context = "\n\nRelevant relationships:\n" + "\n".join(
                f"- {source.name} --[{rel.relationship_type.value}]--> {target.name}"
                for rel, source, target in context_relationships[:5]
            )
        
        prompt = f"""User question: {question}{context}

Provide a helpful, concise answer focused on relationship management."""

        return await self._generate(prompt)
