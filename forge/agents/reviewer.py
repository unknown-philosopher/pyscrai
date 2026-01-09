"""
Reviewer Agent for Forge 3.0.

Reviews extraction quality and suggests improvements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship

logger = get_logger("agents.reviewer")


REVIEWER_SYSTEM_PROMPT = """You are a quality assurance specialist reviewing extracted intelligence data.

Your role is to:
1. Verify extraction accuracy and completeness
2. Identify potential errors or inconsistencies
3. Suggest improvements to entity descriptions
4. Flag entities that may need merging
5. Recommend relationship corrections

REVIEW CRITERIA:
- Accuracy: Is the extracted information correct?
- Completeness: Are important details missing?
- Consistency: Do related entities have consistent information?
- Clarity: Are descriptions clear and useful?
- Relationships: Are connections properly captured?

OUTPUT FORMAT:
Provide structured feedback with:
- Overall quality score (0-100)
- Specific issues found
- Recommended corrections
- Merge suggestions
- Priority for review (HIGH/MEDIUM/LOW)
"""


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
        return REVIEWER_SYSTEM_PROMPT
    
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
        entity_text = self._format_entity(entity)
        
        prompt = f"""Review the following extracted entity for quality issues:

ENTITY:
{entity_text}

{f"ORIGINAL SOURCE TEXT: {source_text[:1000]}" if source_text else ""}

Provide your review with:
1. Quality score (0-100)
2. Issues found (list each issue)
3. Recommended corrections
4. Overall assessment
5. Priority for human review (HIGH/MEDIUM/LOW)

Respond in JSON format:
{{
    "quality_score": <0-100>,
    "issues": ["issue1", "issue2"],
    "corrections": ["correction1", "correction2"],
    "priority": "HIGH|MEDIUM|LOW",
    "notes": "additional notes"
}}"""

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
        entities_text = "\n\n".join(
            f"{i+1}. {self._format_entity(e)}"
            for i, e in enumerate(entities[:15])
        )
        
        prompt = f"""Review the following batch of extracted entities for quality and consistency:

ENTITIES:
{entities_text}

Review for:
1. Individual entity quality
2. Consistency between related entities
3. Potential duplicate entities that should be merged
4. Missing relationships that seem obvious
5. Overall extraction quality

Provide your review in JSON format:
{{
    "overall_score": <0-100>,
    "entity_scores": {{"entity_name": score, ...}},
    "consistency_issues": ["issue1", "issue2"],
    "merge_suggestions": [
        {{"entity1": "name1", "entity2": "name2", "reason": "why"}}
    ],
    "missing_relationships": [
        {{"source": "name", "target": "name", "type": "relationship type"}}
    ],
    "summary": "overall assessment"
}}"""

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
        main_text = self._format_entity(entity)
        related_text = "\n\n".join(
            self._format_entity(e) for e in related_entities[:5]
        )
        
        prompt = f"""Check the following entity for consistency with related entities:

MAIN ENTITY:
{main_text}

RELATED ENTITIES:
{related_text}

Check for:
1. Contradictory information
2. Inconsistent naming or references
3. Timeline inconsistencies
4. Relationship mismatches
5. Missing cross-references

Provide findings in JSON format:
{{
    "is_consistent": true|false,
    "inconsistencies": [
        {{"type": "type", "description": "what's inconsistent", "severity": "HIGH|MEDIUM|LOW"}}
    ],
    "recommendations": ["recommendation1", "recommendation2"],
    "confidence": <0.0-1.0>
}}"""

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
        prompt = f"""Suggest improvements for the following entity:

CURRENT ENTITY:
{self._format_entity(entity)}

Suggest:
1. Description improvements (clearer, more informative)
2. Additional attributes that might be useful
3. Better categorization or type assignment
4. Alias additions
5. Relationship suggestions based on description

Provide in JSON format:
{{
    "improved_description": "suggested new description",
    "suggested_attributes": {{"key": "value"}},
    "suggested_aliases": ["alias1", "alias2"],
    "type_suggestion": "suggested type if different",
    "notes": "additional suggestions"
}}"""

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
        
        entities_text = "\n\n".join(
            f"{i+1}. {self._format_entity(e)}"
            for i, e in enumerate(sample)
        )
        
        stats = self.state.db.get_stats()
        
        prompt = f"""Generate a quality report for this intelligence project.

PROJECT STATISTICS:
- Total Entities: {stats.get('entity_count', 0)}
- Total Relationships: {stats.get('relationship_count', 0)}

SAMPLE ENTITIES (reviewing {len(sample)} of {len(all_entities)}):
{entities_text}

Generate a comprehensive quality report with:
1. Overall data quality assessment
2. Common issues found
3. Strengths of the data
4. Areas needing improvement
5. Recommendations for data cleanup
6. Priority actions

Provide in JSON format:
{{
    "overall_quality": <0-100>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "common_issues": ["issue1", "issue2"],
    "priority_actions": [
        {{"action": "description", "priority": "HIGH|MEDIUM|LOW"}}
    ],
    "recommendations": ["rec1", "rec2"],
    "summary": "executive summary"
}}"""

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
