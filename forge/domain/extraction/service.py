"""Document Extraction Service for PyScrAI Forge.

Extracts entities and relationships from documents using LLM.
"""

import logging
from typing import Optional

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.core.services import BaseLLMService, call_llm_and_parse_json
from forge.infrastructure.llm.base import LLMProvider
from forge.config.prompts import render_prompt

logger = logging.getLogger(__name__)


class DocumentExtractionService(BaseLLMService):
    """Service for extracting entities and relationships from documents."""
    
    def __init__(self, event_bus: EventBus, llm_provider: Optional[LLMProvider] = None):
        """Initialize the document extraction service.
        
        Args:
            event_bus: Event bus for publishing/subscribing to events
            llm_provider: LLM provider for entity extraction (optional, will use default if not provided)
        """
        super().__init__(event_bus, llm_provider, "DocumentExtractionService")

    async def start(self):
        """Start the service and subscribe to events."""
        await self.event_bus.subscribe(events.TOPIC_DATA_INGESTED, self.handle_data_ingested)

    async def handle_data_ingested(self, payload: EventPayload):
        """Handle document ingestion events by extracting entities.
        
        Args:
            payload: Event payload containing doc_id and content
        """
        doc_id = payload.get("doc_id", "unknown")
        content = payload.get("content", "")
        
        if not content or not content.strip():
            logger.warning(f"Document {doc_id} has no content")
            return
        
        # Extract entities using LLM
        entities = await self._extract_entities(doc_id, content)
        
        if entities:
            await self.event_bus.publish(
                events.TOPIC_ENTITY_EXTRACTED,
                {
                    "doc_id": doc_id,
                    "entities": entities,
                },
            )
            logger.info(f"Extracted {len(entities)} entities from document {doc_id}")
        else:
            logger.warning(f"No entities extracted from document {doc_id}")
    
    async def _extract_entities(self, doc_id: str, content: str) -> list[dict]:
        """Extract entities from document content using LLM.
        
        Args:
            doc_id: Document ID
            content: Document content text
            
        Returns:
            List of entity dictionaries with 'type' and 'text' keys
        """
        if not await self.ensure_llm_provider():
            return []
        
        # Type assertion: ensure_llm_provider() guarantees llm_provider is not None
        assert self.llm_provider is not None, "LLM provider should be available after ensure_llm_provider()"
        llm_provider = self.llm_provider
        
        # Render prompt using Jinja2 template
        prompt = render_prompt("extraction_service", content=content)
        
        # Call LLM and parse JSON response
        entities = await call_llm_and_parse_json(
            llm_provider=llm_provider,
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
            service_name=self.service_name,
            doc_id=doc_id
        )
        
        if entities is None:
            return []
        
        # Validate and normalize entities
        if not isinstance(entities, list):
            logger.error(f"{self.service_name}: LLM returned non-list entity data: {type(entities)}")
            return []
        
        # Normalize entity format
        normalized_entities = []
        for entity in entities:
            if isinstance(entity, dict) and "type" in entity and "text" in entity:
                normalized_entities.append({
                    "type": str(entity["type"]).upper(),
                    "text": str(entity["text"]).strip()
                })
        
        return normalized_entities
