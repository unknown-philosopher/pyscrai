"""
OSINT Advisor - AI assistant for Phase 0: Extraction.

Provides guidance for document extraction, entity discovery, and extraction quality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity

logger = get_logger("advisors.osint")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


class OSINTAdvisor(Agent):
    """AI advisor for the extraction phase (OSINT).
    
    Provides intelligent assistance during document extraction,
    helping users analyze source documents, review extraction
    quality, and improve entity discovery.
    
    Usage:
        advisor = OSINTAdvisor(state)
        response = await advisor.analyze_document(text)
        response = await advisor.suggest_improvements(entities, source_text)
    """
    
    role = AgentRole.ADVISOR
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("osint.system_prompt")
    
    async def analyze_document(
        self,
        document_text: str,
    ) -> AgentResponse:
        """Analyze a document for extraction potential.
        
        Args:
            document_text: The document text to analyze
            
        Returns:
            Analysis response with extraction recommendations
        """
        prompt = _prompt_manager.render(
            "osint.analyze_document_prompt",
            document_text=document_text,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log("Analyzed document for extraction")
        
        return response
    
    async def suggest_extraction_improvements(
        self,
        entities: list["Entity"],
        source_text: str,
    ) -> AgentResponse:
        """Suggest improvements to extraction results.
        
        Args:
            entities: Extracted entities to review
            source_text: Original source text
            
        Returns:
            Improvement suggestions
        """
        entity_data = [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description
            }
            for e in entities[:15]
        ]
        
        prompt = _prompt_manager.render(
            "osint.suggest_extraction_improvements_prompt",
            entities=entity_data,
            source_text=source_text,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Reviewed {len(entities)} extracted entities")
        
        return response
    
    async def review_chunk(
        self,
        chunk_text: str,
        chunk_index: int,
        total_chunks: int,
    ) -> AgentResponse:
        """Review a text chunk before extraction.
        
        Args:
            chunk_text: The chunk text to review
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            
        Returns:
            Chunk review response
        """
        prompt = _prompt_manager.render(
            "osint.review_chunk_prompt",
            chunk_text=chunk_text,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Reviewed chunk {chunk_index}/{total_chunks}")
        
        return response
    
    async def answer_question(
        self,
        question: str,
        context: str = "",
    ) -> AgentResponse:
        """Answer a question about extraction.
        
        Args:
            question: User's question
            context: Optional context
            
        Returns:
            Answer response
        """
        prompt = _prompt_manager.render(
            "osint.answer_question_prompt",
            question=question,
            context=context,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Answered question: {question[:50]}...")
        
        return response
