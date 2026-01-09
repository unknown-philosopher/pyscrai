"""
SIGINT Advisor - AI assistant for Phase 2: Relationships.

Provides guidance for relationship analysis, network mapping, and connection management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship

logger = get_logger("advisors.sigint")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


class SIGINTAdvisor(Agent):
    """AI advisor for the relationship phase (SIGINT).
    
    Provides intelligent assistance for relationship management,
    helping users analyze networks, suggest connections, and
    resolve conflicts.
    
    Usage:
        advisor = SIGINTAdvisor(state)
        response = await advisor.suggest_relationship_type(source, target)
        response = await advisor.analyze_network(entities, relationships)
    """
    
    role = AgentRole.ADVISOR
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("sigint.system_prompt")
    
    async def suggest_relationship_type(
        self,
        source: "Entity",
        target: "Entity",
    ) -> AgentResponse:
        """Suggest relationship type between two entities.
        
        Args:
            source: Source entity
            target: Target entity
            
        Returns:
            Response with relationship suggestions
        """
        prompt = _prompt_manager.render(
            "sigint.suggest_relationship_type_prompt",
            source_name=source.name,
            source_type=source.type.value,
            source_description=source.description,
            target_name=target.name,
            target_type=target.type.value,
            target_description=target.description,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Suggested relationship: {source.name} -> {target.name}")
        
        return response
    
    async def analyze_relationship(
        self,
        relationship: "Relationship",
        source: "Entity",
        target: "Entity",
    ) -> AgentResponse:
        """Analyze an existing relationship.
        
        Args:
            relationship: Relationship to analyze
            source: Source entity
            target: Target entity
            
        Returns:
            Analysis response
        """
        prompt = _prompt_manager.render(
            "sigint.analyze_relationship_prompt",
            relationship_type=relationship.type.value,
            relationship_strength=relationship.strength,
            relationship_description=relationship.description,
            source_name=source.name,
            source_type=source.type.value,
            target_name=target.name,
            target_type=target.type.value,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Analyzed relationship: {source.name} -> {target.name}")
        
        return response
    
    async def find_missing_relationships(
        self,
        entity: "Entity",
        existing_relationships: list[dict],
        other_entities: list["Entity"],
    ) -> AgentResponse:
        """Identify potentially missing relationships.
        
        Args:
            entity: Entity to analyze
            existing_relationships: Current relationships (dicts with type, target_name)
            other_entities: Other entities in the world
            
        Returns:
            Response with missing relationship suggestions
        """
        other_data = [
            {"name": e.name, "type": e.type.value}
            for e in other_entities[:15]
        ]
        
        prompt = _prompt_manager.render(
            "sigint.find_missing_relationships_prompt",
            entity_name=entity.name,
            entity_type=entity.type.value,
            entity_description=entity.description,
            existing_relationships=existing_relationships,
            other_entities=other_data,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Found missing relationships for '{entity.name}'")
        
        return response
    
    async def resolve_conflict(
        self,
        source_a_name: str,
        target_a_name: str,
        type_a: str,
        strength_a: float,
        source_b_name: str,
        target_b_name: str,
        type_b: str,
        strength_b: float,
    ) -> AgentResponse:
        """Help resolve conflicting relationships.
        
        Args:
            source_a_name, target_a_name, type_a, strength_a: First relationship
            source_b_name, target_b_name, type_b, strength_b: Second relationship
            
        Returns:
            Resolution recommendation
        """
        prompt = _prompt_manager.render(
            "sigint.resolve_conflict_prompt",
            source_a_name=source_a_name,
            target_a_name=target_a_name,
            type_a=type_a,
            strength_a=strength_a,
            source_b_name=source_b_name,
            target_b_name=target_b_name,
            type_b=type_b,
            strength_b=strength_b,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log("Provided conflict resolution recommendation")
        
        return response
    
    async def analyze_network(
        self,
        entities: list["Entity"],
        relationships: list[dict],
    ) -> AgentResponse:
        """Analyze a relationship network.
        
        Args:
            entities: Entities in the network
            relationships: Relationships (dicts with source, target, type, strength)
            
        Returns:
            Network analysis response
        """
        entity_data = [
            {"name": e.name, "type": e.type.value}
            for e in entities[:20]
        ]
        
        prompt = _prompt_manager.render(
            "sigint.analyze_network_prompt",
            entities=entity_data,
            relationships=relationships[:30],
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Analyzed network with {len(entities)} entities")
        
        return response
    
    async def answer_question(
        self,
        question: str,
        context_relationships: list[dict] | None = None,
    ) -> AgentResponse:
        """Answer a question about relationships.
        
        Args:
            question: User's question
            context_relationships: Relevant relationships (dicts with source, target, type)
            
        Returns:
            Response to the question
        """
        prompt = _prompt_manager.render(
            "sigint.answer_question_prompt",
            question=question,
            context_relationships=context_relationships or [],
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Answered question: {question[:50]}...")
        
        return response
