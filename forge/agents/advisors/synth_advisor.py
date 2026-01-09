"""
SYNTH Advisor - AI assistant for Phase 3: Narrative.

Provides guidance for narrative generation, storytelling, and worldbuilding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity

logger = get_logger("advisors.synth")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


class SYNTHAdvisor(Agent):
    """AI advisor for the narrative phase (SYNTH).
    
    Provides intelligent assistance for narrative generation,
    helping users create stories, dialogue, and develop their
    world's lore.
    
    Usage:
        advisor = SYNTHAdvisor(state)
        response = await advisor.generate_narrative(entities, relationships)
        response = await advisor.suggest_story_arc(characters, relationships)
    """
    
    role = AgentRole.ADVISOR
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("synth.system_prompt")
    
    async def generate_narrative(
        self,
        entities: list["Entity"],
        relationships: list[dict],
        setting: str = "",
        tone: str = "",
        focus: str = "",
    ) -> AgentResponse:
        """Generate a narrative passage.
        
        Args:
            entities: Entities to feature
            relationships: Relationships between entities
            setting: Optional setting description
            tone: Optional tone (e.g., "dark", "hopeful")
            focus: Optional focus area
            
        Returns:
            Generated narrative response
        """
        entity_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in entities[:6]
        ]
        
        prompt = _prompt_manager.render(
            "synth.generate_narrative_prompt",
            entities=entity_data,
            relationships=relationships[:10],
            setting=setting,
            tone=tone,
            focus=focus,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Generated narrative with {len(entities)} entities")
        
        return response
    
    async def suggest_story_arc(
        self,
        characters: list["Entity"],
        relationships: list[dict],
        theme: str = "",
        conflict_type: str = "",
    ) -> AgentResponse:
        """Suggest a story arc.
        
        Args:
            characters: Main characters
            relationships: Key relationships
            theme: Optional theme
            conflict_type: Optional conflict type
            
        Returns:
            Story arc suggestions
        """
        char_data = [
            {
                "name": c.name,
                "description": c.description
            }
            for c in characters[:5]
        ]
        
        prompt = _prompt_manager.render(
            "synth.suggest_story_arc_prompt",
            characters=char_data,
            relationships=relationships[:10],
            theme=theme,
            conflict_type=conflict_type,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log("Suggested story arc")
        
        return response
    
    async def identify_narrative_gaps(
        self,
        entities: list["Entity"],
        relationships: list[dict],
    ) -> AgentResponse:
        """Identify narrative gaps and opportunities.
        
        Args:
            entities: World entities
            relationships: World relationships
            
        Returns:
            Gap analysis response
        """
        entity_data = [
            {"name": e.name, "type": e.type.value}
            for e in entities[:20]
        ]
        
        prompt = _prompt_manager.render(
            "synth.identify_narrative_gaps_prompt",
            entities=entity_data,
            relationships=relationships[:20],
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log("Identified narrative gaps")
        
        return response
    
    async def generate_dialogue(
        self,
        characters: list["Entity"],
        relationship_context: str,
        situation: str,
        tone: str = "",
    ) -> AgentResponse:
        """Generate dialogue between characters.
        
        Args:
            characters: Characters in the scene
            relationship_context: How they relate to each other
            situation: The current situation
            tone: Optional tone
            
        Returns:
            Generated dialogue
        """
        char_data = [
            {
                "name": c.name,
                "type": c.type.value,
                "description": c.description
            }
            for c in characters[:4]
        ]
        
        prompt = _prompt_manager.render(
            "synth.generate_dialogue_prompt",
            characters=char_data,
            relationship_context=relationship_context,
            situation=situation,
            tone=tone,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            names = ", ".join(c.name for c in characters[:4])
            self.log(f"Generated dialogue for: {names}")
        
        return response
    
    async def answer_question(
        self,
        question: str,
        context: str = "",
    ) -> AgentResponse:
        """Answer a question about narrative.
        
        Args:
            question: User's question
            context: Optional context
            
        Returns:
            Response to the question
        """
        prompt = _prompt_manager.render(
            "synth.answer_question_prompt",
            question=question,
            context=context,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Answered question: {question[:50]}...")
        
        return response
