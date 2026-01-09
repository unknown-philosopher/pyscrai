"""
Analyst Agent for Forge 3.0.

Provides deep analysis of entities and relationships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship

logger = get_logger("agents.analyst")


ANALYST_SYSTEM_PROMPT = """You are an expert intelligence analyst specializing in narrative and network analysis.

Your capabilities:
1. ENTITY ANALYSIS: Deep analysis of individuals, organizations, and concepts
2. RELATIONSHIP ANALYSIS: Understanding connections, power dynamics, and influence
3. PATTERN RECOGNITION: Identifying trends, anomalies, and hidden connections
4. STRATEGIC ASSESSMENT: Evaluating capabilities, intentions, and likely actions

GUIDELINES:
- Be objective and evidence-based
- Note confidence levels for assessments
- Identify gaps in available information
- Consider multiple hypotheses
- Structure analysis clearly

When analyzing entities, consider:
- Background and history
- Capabilities and resources
- Motivations and goals
- Relationships and alliances
- Vulnerabilities and weaknesses
- Recent activities and trends

When analyzing relationships, consider:
- Nature of the connection
- Power balance
- Historical context
- Current status
- Strategic implications
"""


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
        return ANALYST_SYSTEM_PROMPT
    
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
        
        prompt = f"""Analyze the following entity in detail:

{entity_text}

RELATIONSHIPS:
{rel_text if rel_text else "No known relationships."}

{f"ADDITIONAL CONTEXT: {context}" if context else ""}

Provide a comprehensive analysis including:
1. Summary assessment
2. Key characteristics
3. Network position and influence
4. Potential motivations
5. Risk assessment
6. Information gaps

Be thorough but concise."""

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
        prompt = f"""Analyze the following relationship:

SOURCE ENTITY:
{self._format_entity(source)}

TARGET ENTITY:
{self._format_entity(target)}

RELATIONSHIP:
- Type: {relationship.type.value}
- Description: {relationship.description or "Not specified"}
- Strength: {relationship.strength} (-1.0 hostile to 1.0 allied)

{f"ADDITIONAL CONTEXT: {context}" if context else ""}

Provide analysis including:
1. Nature of the relationship
2. Power dynamics
3. Historical context (if apparent)
4. Strategic implications
5. Potential developments
6. Confidence assessment"""

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
        entities_text = "\n\n".join(
            f"ENTITY {i+1}:\n{self._format_entity(e)}"
            for i, e in enumerate(entities)
        )
        
        prompt = f"""Compare and contrast the following entities:

{entities_text}

Provide analysis including:
1. Key similarities
2. Key differences
3. Relative capabilities/influence
4. Relationship dynamics
5. Strategic positioning
6. Comparison summary table"""

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
        entities_text = "\n\n".join(
            self._format_entity(e) for e in entities[:10]
        )
        
        prompt = f"""Generate a strategic intelligence assessment based on these entities:

{entities_text}

{f"FOCUS AREA: {focus_area}" if focus_area else ""}

Provide a structured assessment including:
1. EXECUTIVE SUMMARY: Key findings in 2-3 sentences
2. KEY ACTORS: Most significant entities and their roles
3. NETWORK DYNAMICS: Major relationships and power structures
4. TRENDS: Emerging patterns and developments
5. RISKS: Potential threats and vulnerabilities
6. OPPORTUNITIES: Potential leverage points
7. INTELLIGENCE GAPS: What we need to know more about
8. RECOMMENDATIONS: Suggested actions or monitoring priorities"""

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
        context = ""
        if relevant_entities:
            context = "RELEVANT ENTITIES:\n" + "\n\n".join(
                self._format_entity(e) for e in relevant_entities[:5]
            )
        
        prompt = f"""Answer the following analytical question:

QUESTION: {question}

{context}

Provide:
1. Direct answer to the question
2. Supporting evidence/reasoning
3. Confidence level
4. Alternative interpretations if applicable
5. Recommendations for further investigation"""

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
