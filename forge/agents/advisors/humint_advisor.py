"""
HUMINT Advisor - AI assistant for Phase 1: Entities.

Provides guidance for entity refinement, management, and quality improvement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity

logger = get_logger("advisors.humint")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


class HUMINTAdvisor(Agent):
    """AI advisor for the entity phase (HUMINT).
    
    Provides intelligent assistance for entity management,
    helping users refine entities, suggest relationships,
    and maintain consistency.
    
    Usage:
        advisor = HUMINTAdvisor(state)
        response = await advisor.suggest_improvements(entity)
        response = await advisor.help_merge_decision(entity_a, entity_b)
    """
    
    role = AgentRole.ADVISOR
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("humint.system_prompt")
    
    async def suggest_improvements(
        self,
        entity: "Entity",
    ) -> AgentResponse:
        """Suggest improvements for an entity.
        
        Args:
            entity: Entity to analyze
            
        Returns:
            Response with improvement suggestions
        """
        prompt = _prompt_manager.render(
            "humint.suggest_improvements_prompt",
            entity_name=entity.name,
            entity_type=entity.type.value,
            entity_description=entity.description,
            entity_aliases=entity.aliases,
            entity_attributes=entity.attributes,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Suggested improvements for '{entity.name}'")
        
        return response
    
    async def suggest_relationships(
        self,
        entity: "Entity",
        other_entities: list["Entity"],
    ) -> AgentResponse:
        """Suggest relationships between entities.
        
        Args:
            entity: Primary entity
            other_entities: Other entities to consider
            
        Returns:
            Response with relationship suggestions
        """
        other_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in other_entities[:10]
        ]
        
        prompt = _prompt_manager.render(
            "humint.suggest_relationships_prompt",
            entity_name=entity.name,
            entity_type=entity.type.value,
            entity_description=entity.description,
            other_entities=other_data,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Suggested relationships for '{entity.name}'")
        
        return response
    
    async def help_merge_decision(
        self,
        entity_a: "Entity",
        entity_b: "Entity",
    ) -> AgentResponse:
        """Help decide whether to merge two entities.
        
        Args:
            entity_a: First entity
            entity_b: Second entity
            
        Returns:
            Response with merge recommendation
        """
        prompt = _prompt_manager.render(
            "humint.help_merge_decision_prompt",
            entity_a_name=entity_a.name,
            entity_a_type=entity_a.type.value,
            entity_a_description=entity_a.description,
            entity_a_aliases=entity_a.aliases,
            entity_b_name=entity_b.name,
            entity_b_type=entity_b.type.value,
            entity_b_description=entity_b.description,
            entity_b_aliases=entity_b.aliases,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Merge analysis: '{entity_a.name}' vs '{entity_b.name}'")
        
        return response
    
    async def answer_question(
        self,
        question: str,
        context_entities: list["Entity"] | None = None,
    ) -> AgentResponse:
        """Answer a question about entities.
        
        Args:
            question: User's question
            context_entities: Relevant entities for context
            
        Returns:
            Response to the question
        """
        context_data = []
        if context_entities:
            context_data = [
                {
                    "name": e.name,
                    "type": e.type.value,
                    "description": e.description
                }
                for e in context_entities[:5]
            ]
        
        prompt = _prompt_manager.render(
            "humint.answer_question_prompt",
            question=question,
            context_entities=context_data,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Answered question: {question[:50]}...")
        
        return response
