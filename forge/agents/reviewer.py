"""
Reviewer Agent for Forge 3.0.

Reviews extraction quality and suggests improvements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship

logger = get_logger("agents.reviewer")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


@dataclass
class ReviewResult:
    """Result of a review operation."""
    
    quality_score: int  # 0-100
    issues: list[str]
    corrections: list[str]
    merge_suggestions: list[tuple[str, str]]  # Pairs of entity IDs to merge
    priority: str  # HIGH/MEDIUM/LOW
    notes: str = ""


class ReviewerAgent(Agent):
    """Agent for reviewing extraction quality.
    
    Usage:
        reviewer = ReviewerAgent(state)
        
        # Review an entity
        response = await reviewer.review_entity(entity)
        
        # Review a batch
        response = await reviewer.review_batch(entities)
        
        # Get quality report
        response = await reviewer.quality_report()
    """
    
    role = AgentRole.REVIEWER
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("review.system_prompt")
    
    async def review_entity(
        self,
        entity: "Entity",
        source_text: str = "",
    ) -> AgentResponse:
        """Review a single entity for quality issues.
        
        Args:
            entity: Entity to review
            source_text: Original source text for comparison
            
        Returns:
            Review response
        """
        # Render prompt template with variables
        prompt = _prompt_manager.render(
            "review.review_entity_prompt",
            entity_name=entity.name,
            entity_type=entity.type.value,
            entity_description=entity.description,
            entity_aliases=entity.aliases,
            source_text=source_text,
        )

        response = await self._generate_structured(prompt)
        
        if response.success and response.structured_data:
            self.log(
                f"Reviewed entity '{entity.name}': "
                f"score={response.structured_data.get('quality_score', 'N/A')}"
            )
        
        return response
    
    async def review_batch(
        self,
        entities: list["Entity"],
    ) -> AgentResponse:
        """Review a batch of entities for quality and consistency.
        
        Args:
            entities: Entities to review
            
        Returns:
            Batch review response
        """
        # Format entities for rendering
        entity_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in entities[:15]
        ]
        
        # Render prompt template
        prompt = _prompt_manager.render(
            "review.review_batch_prompt",
            entities=entity_data,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Reviewed batch of {len(entities)} entities")
        
        return response
    
    async def check_consistency(
        self,
        entity: "Entity",
        related_entities: list["Entity"],
    ) -> AgentResponse:
        """Check an entity for consistency with related entities.
        
        Args:
            entity: Primary entity to check
            related_entities: Related entities for comparison
            
        Returns:
            Consistency check response
        """
        # Format related entities for rendering
        related_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in related_entities[:5]
        ]
        
        # Render prompt template
        prompt = _prompt_manager.render(
            "review.check_consistency_prompt",
            main_entity_name=entity.name,
            main_entity_type=entity.type.value,
            main_entity_description=entity.description,
            related_entities=related_data,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Consistency check for '{entity.name}'")
        
        return response
    
    async def suggest_improvements(
        self,
        entity: "Entity",
    ) -> AgentResponse:
        """Suggest improvements for an entity's description.
        
        Args:
            entity: Entity to improve
            
        Returns:
            Improvement suggestions
        """
        # Render prompt template
        prompt = _prompt_manager.render(
            "review.suggest_improvements_prompt",
            entity_name=entity.name,
            entity_type=entity.type.value,
            entity_description=entity.description,
            entity_aliases=entity.aliases,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Generated improvements for '{entity.name}'")
        
        return response
    
    async def quality_report(
        self,
        sample_size: int = 20,
    ) -> AgentResponse:
        """Generate a quality report for the project.
        
        Args:
            sample_size: Number of entities to sample
            
        Returns:
            Quality report response
        """
        # Get a sample of entities
        all_entities = self.state.db.get_all_entities()
        
        if len(all_entities) <= sample_size:
            sample = all_entities
        else:
            import random
            sample = random.sample(all_entities, sample_size)
        
        # Format entities for rendering
        sample_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in sample
        ]
        
        stats = self.state.db.get_stats()
        
        # Render prompt template
        prompt = _prompt_manager.render(
            "review.quality_report_prompt",
            total_entities=stats.get('entity_count', 0),
            total_relationships=stats.get('relationship_count', 0),
            sample_entities=sample_data,
            sample_count=len(sample),
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Generated quality report (sampled {len(sample)} entities)")
        
        return response
    
    def _format_entity(self, entity: "Entity") -> str:
        """Format an entity for prompts."""
        lines = [
            f"Name: {entity.name}",
            f"Type: {entity.type.value}",
        ]
        
        if entity.description:
            lines.append(f"Description: {entity.description}")
        
        if entity.aliases:
            lines.append(f"Aliases: {', '.join(entity.aliases)}")
        
        for key, value in entity.attributes.items():
            lines.append(f"{key}: {value}")
        
        return "\n".join(lines)
