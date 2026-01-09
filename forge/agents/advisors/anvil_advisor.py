"""
ANVIL Advisor - AI assistant for Phase 5: Finalize.

Provides guidance for final quality checks, merging, and export preparation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity

logger = get_logger("advisors.anvil")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


class ANVILAdvisor(Agent):
    """AI advisor for the finalization phase (ANVIL).
    
    Provides intelligent assistance for final quality checks,
    merge decisions, consistency validation, and export preparation.
    
    Usage:
        advisor = ANVILAdvisor(state)
        response = await advisor.final_review(entity, relationships)
        response = await advisor.export_readiness(stats, samples)
    """
    
    role = AgentRole.ADVISOR
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("anvil.system_prompt")
    
    async def final_review(
        self,
        entity: "Entity",
        relationships: list[dict],
    ) -> AgentResponse:
        """Perform a final review of an entity.
        
        Args:
            entity: Entity to review
            relationships: Entity's relationships
            
        Returns:
            Final review response
        """
        prompt = _prompt_manager.render(
            "anvil.final_review_prompt",
            entity_name=entity.name,
            entity_type=entity.type.value,
            entity_description=entity.description,
            entity_aliases=entity.aliases,
            entity_attributes=entity.attributes,
            relationships=relationships,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Final review for '{entity.name}'")
        
        return response
    
    async def merge_analysis(
        self,
        entities: list["Entity"],
    ) -> AgentResponse:
        """Analyze entities for potential merge.
        
        Args:
            entities: Entities to analyze (typically 2-3)
            
        Returns:
            Merge analysis response
        """
        entity_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description,
                "aliases": e.aliases
            }
            for e in entities[:5]
        ]
        
        prompt = _prompt_manager.render(
            "anvil.merge_analysis_prompt",
            entities=entity_data,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            names = ", ".join(e.name for e in entities)
            self.log(f"Merge analysis for: {names}")
        
        return response
    
    async def consistency_check(
        self,
        entities: list["Entity"],
        relationships: list[dict],
    ) -> AgentResponse:
        """Check consistency across related entities.
        
        Args:
            entities: Related entities to check
            relationships: Relationships between them
            
        Returns:
            Consistency check response
        """
        entity_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in entities[:10]
        ]
        
        prompt = _prompt_manager.render(
            "anvil.consistency_check_prompt",
            entities=entity_data,
            relationships=relationships[:20],
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Consistency check for {len(entities)} entities")
        
        return response
    
    async def export_readiness(
        self,
        entity_count: int,
        relationship_count: int,
        entity_types: list[str],
        sample_entities: list["Entity"],
        sample_relationships: list[dict],
    ) -> AgentResponse:
        """Assess export readiness for the world.
        
        Args:
            entity_count: Total entity count
            relationship_count: Total relationship count
            entity_types: List of entity types present
            sample_entities: Sample entities for review
            sample_relationships: Sample relationships for review
            
        Returns:
            Export readiness assessment
        """
        sample_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in sample_entities[:10]
        ]
        
        prompt = _prompt_manager.render(
            "anvil.export_readiness_prompt",
            entity_count=entity_count,
            relationship_count=relationship_count,
            entity_types=entity_types,
            sample_entities=sample_data,
            sample_relationships=sample_relationships[:10],
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log("Assessed export readiness")
        
        return response
    
    async def answer_question(
        self,
        question: str,
        context: str = "",
    ) -> AgentResponse:
        """Answer a question about finalization.
        
        Args:
            question: User's question
            context: Optional context
            
        Returns:
            Response to the question
        """
        prompt = _prompt_manager.render(
            "anvil.answer_question_prompt",
            question=question,
            context=context,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Answered question: {question[:50]}...")
        
        return response
