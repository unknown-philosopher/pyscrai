"""Document Extraction Service for PyScrAI Forge.

Extracts entities and relationships from documents using LLM.
"""

import asyncio
import json
import logging
from typing import Optional

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.infrastructure.llm.base import LLMProvider
from forge.config.prompts import render_prompt

logger = logging.getLogger(__name__)


class DocumentExtractionService:
    """Service for extracting entities and relationships from documents."""
    
    def __init__(self, event_bus: EventBus, llm_provider: Optional[LLMProvider] = None):
        """Initialize the document extraction service.
        
        Args:
            event_bus: Event bus for publishing/subscribing to events
            llm_provider: LLM provider for entity extraction (optional, will use default if not provided)
        """
        self.event_bus = event_bus
        self.llm_provider = llm_provider

    async def start(self):
        """Start the service and subscribe to events."""
        await self.event_bus.subscribe(events.TOPIC_DATA_INGESTED, self.handle_data_ingested)
        
        # If no LLM provider was provided, try to get one from environment
        if self.llm_provider is None:
            try:
                from forge.infrastructure.llm.provider_factory import ProviderFactory
                self.llm_provider, _ = ProviderFactory.create_from_env()
                logger.info("DocumentExtractionService: Using LLM provider from environment")
            except Exception as e:
                logger.warning(f"DocumentExtractionService: Could not initialize LLM provider: {e}")
                logger.warning("DocumentExtractionService: Entity extraction will be disabled")

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
        if not self.llm_provider:
            logger.error("No LLM provider available for entity extraction")
            return []
        
        # Render prompt using Jinja2 template
        prompt = render_prompt("extraction_service", content=content)
        
        content_text = ""
        try:
            # Get available models
            models = await self.llm_provider.list_models()
            model = models[0].id if models else self.llm_provider.default_model
            if not model:
                logger.error("No model available for entity extraction")
                return []
            
            response = await self.llm_provider.complete(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                max_tokens=2000,
                temperature=0.3,
            )
            
            # Parse JSON response
            if "choices" in response and response["choices"]:
                content_text = response["choices"][0].get("message", {}).get("content", "")
            
            if not content_text:
                logger.warning(f"No content in LLM response for document {doc_id}")
                return []
            
            # Clean up the response (remove markdown code blocks if present)
            content_text = content_text.strip()
            if content_text.startswith("```"):
                # Remove markdown code block markers
                lines = content_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                content_text = "\n".join(lines).strip()
            
            entities = json.loads(content_text)
            
            # Validate and normalize entities
            if not isinstance(entities, list):
                logger.error(f"LLM returned non-list entity data: {type(entities)}")
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
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON for document {doc_id}: {e}")
            logger.debug(f"Response content: {content_text}")
            return []
        except Exception as e:
            logger.error(f"Error extracting entities from document {doc_id}: {e}", exc_info=True)
            return []
