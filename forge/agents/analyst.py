"""
Analyst Agent for Forge 3.0.

Provides deep analysis of entities and relationships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship

logger = get_logger("agents.analyst")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


class AnalystAgent(Agent):
    """Agent for deep analysis of entities and relationships.
    
    Usage:
        analyst = AnalystAgent(state)
        
        # Analyze an entity
        response = await analyst.analyze_entity(entity)
        print(response.content)
        
        # Analyze a relationship
        response = await analyst.analyze_relationship(rel, source, target)
        
        # Get strategic assessment
        response = await analyst.strategic_assessment(entities)
    """
    
    role = AgentRole.ANALYST
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("analysis.system_prompt")
    
    async def analyze_entity(
        self,
        entity: "Entity",
        context: str = "",
    ) -> AgentResponse:
        """Perform deep analysis on an entity.
        
        Args:
            entity: Entity to analyze
            context: Additional context about the project
            
        Returns:
            Analysis response
        """
        # Build entity description
        entity_text = self._format_entity(entity)
        
        # Get relationships for context
        relationships = self.state.db.get_relationships_for_entity(entity.id)
        rel_text = self._format_relationships(entity.id, relationships)
        
        # Render prompt template with variables
        prompt = _prompt_manager.render(
            "analysis.analyze_entity_prompt",
            entity_name=entity.name,
            entity_type=entity.type.value,
            entity_description=entity.description,
            entity_aliases=entity.aliases,
            relationships=rel_text,
            additional_context=context,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Analyzed entity: {entity.name}")
        
        return response
    
    async def analyze_relationship(
        self,
        relationship: "Relationship",
        source: "Entity",
        target: "Entity",
        context: str = "",
    ) -> AgentResponse:
        """Analyze a relationship between entities.
        
        Args:
            relationship: The relationship to analyze
            source: Source entity
            target: Target entity
            context: Additional context
            
        Returns:
            Analysis response
        """
        # Render prompt template with variables
        prompt = _prompt_manager.render(
            "analysis.analyze_relationship_prompt",
            source_name=source.name,
            source_type=source.type.value,
            source_description=source.description,
            target_name=target.name,
            target_type=target.type.value,
            target_description=target.description,
            relationship_type=relationship.type.value,
            relationship_description=relationship.description or "Not specified",
            relationship_strength=relationship.strength,
            additional_context=context,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Analyzed relationship: {source.name} -> {target.name}")
        
        return response
    
    async def compare_entities(
        self,
        entities: list["Entity"],
    ) -> AgentResponse:
        """Compare multiple entities.
        
        Args:
            entities: List of entities to compare
            
        Returns:
            Comparison analysis
        """
        # Format entities for rendering
        entity_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in entities
        ]
        
        # Render prompt template
        prompt = _prompt_manager.render(
            "analysis.compare_entities_prompt",
            entities=entity_data,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            names = ", ".join(e.name for e in entities)
            self.log(f"Compared entities: {names}")
        
        return response
    
    async def strategic_assessment(
        self,
        entities: list["Entity"],
        focus_area: str = "",
    ) -> AgentResponse:
        """Generate a strategic assessment.
        
        Args:
            entities: Entities to include in assessment
            focus_area: Optional focus area for the assessment
            
        Returns:
            Strategic assessment
        """
        # Format entities for rendering
        entity_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in entities[:10]
        ]
        
        # Render prompt template
        prompt = _prompt_manager.render(
            "analysis.strategic_assessment_prompt",
            entities=entity_data,
            focus_area=focus_area,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Generated strategic assessment for {len(entities)} entities")
        
        return response
    
    async def answer_question(
        self,
        question: str,
        relevant_entities: list["Entity"] | None = None,
    ) -> AgentResponse:
        """Answer an analytical question.
        
        Args:
            question: The question to answer
            relevant_entities: Entities relevant to the question
            
        Returns:
            Answer response
        """
        # Format entities for rendering
        entity_data = []
        if relevant_entities:
            entity_data = [
                {
                    "name": e.name,
                    "type": e.type.value,
                    "description": e.description
                }
                for e in relevant_entities[:5]
            ]
        
        # Render prompt template
        prompt = _prompt_manager.render(
            "analysis.answer_question_prompt",
            question=question,
            relevant_entities=entity_data,
        )

        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Answered question: {question[:50]}...")
        
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
        
        # Include relevant attributes
        for key, value in entity.attributes.items():
            if key not in ("extraction_confidence", "source_document"):
                lines.append(f"{key}: {value}")
        
        return "\n".join(lines)
    
    def _format_relationships(
        self,
        entity_id: str,
        relationships: list["Relationship"],
    ) -> str:
        """Format relationships for prompts."""
        if not relationships:
            return ""
        
        lines = []
        for rel in relationships[:10]:
            if rel.source_id == entity_id:
                direction = "->"
                other_id = rel.target_id
            else:
                direction = "<-"
                other_id = rel.source_id
            
            # Get other entity name
            other = self.state.db.get_entity(other_id)
            other_name = other.name if other else other_id
            
            lines.append(
                f"- {rel.type.value} {direction} {other_name}"
                f" (strength: {rel.strength:.1f})"
            )
        
        return "\n".join(lines)
