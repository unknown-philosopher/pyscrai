"""Real-time Intelligence Streaming Service for PyScrAI Forge.

Provides real-time streaming of intelligence updates to the UI.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional, AsyncIterator
from collections import deque

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events

logger = logging.getLogger(__name__)


class IntelligenceStreamingService:
    """Service for streaming real-time intelligence updates."""
    
    def __init__(self, event_bus: EventBus):
        """Initialize the streaming service.
        
        Args:
            event_bus: Event bus for subscribing to intelligence events
        """
        self.event_bus = event_bus
        self.service_name = "IntelligenceStreamingService"
        
        # Stream buffers for different intelligence types
        self._stream_buffers: Dict[str, deque] = {
            "semantic_profiles": deque(maxlen=100),
            "narratives": deque(maxlen=50),
            "graph_analytics": deque(maxlen=50),
            "entities": deque(maxlen=200),
        }
        
        # Active stream subscriptions
        self._active_streams: Dict[str, asyncio.Queue] = {}
        
    async def start(self):
        """Start the service and subscribe to intelligence events."""
        logger.info("Starting IntelligenceStreamingService")
        
        # Subscribe to intelligence events
        await self.event_bus.subscribe(events.TOPIC_SEMANTIC_PROFILE, self._handle_semantic_profile)
        await self.event_bus.subscribe(events.TOPIC_NARRATIVE_GENERATED, self._handle_narrative)
        await self.event_bus.subscribe(events.TOPIC_GRAPH_ANALYSIS, self._handle_graph_analysis)
        await self.event_bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, self._handle_entity_extracted)
        await self.event_bus.subscribe(events.TOPIC_ENTITY_MERGED, self._handle_entity_merged)
        
        logger.info("IntelligenceStreamingService started")
    
    async def _handle_semantic_profile(self, payload: EventPayload):
        """Handle semantic profile events."""
        profile = payload.get("profile")
        if profile:
            self._stream_buffers["semantic_profiles"].append({
                "type": "semantic_profile",
                "data": profile,
                "timestamp": payload.get("timestamp"),
            })
            await self._broadcast_update("semantic_profiles", profile)
    
    async def _handle_narrative(self, payload: EventPayload):
        """Handle narrative generation events."""
        narrative = payload.get("narrative")
        if narrative:
            self._stream_buffers["narratives"].append({
                "type": "narrative",
                "data": narrative,
                "timestamp": payload.get("timestamp"),
            })
            await self._broadcast_update("narratives", narrative)
    
    async def _handle_graph_analysis(self, payload: EventPayload):
        """Handle graph analysis events."""
        analysis = payload.get("analysis")
        if analysis:
            self._stream_buffers["graph_analytics"].append({
                "type": "graph_analytics",
                "data": analysis,
                "timestamp": payload.get("timestamp"),
            })
            await self._broadcast_update("graph_analytics", analysis)
    
    async def _handle_entity_extracted(self, payload: EventPayload):
        """Handle entity extraction events."""
        entities = payload.get("entities", [])
        for entity in entities:
            self._stream_buffers["entities"].append({
                "type": "entity",
                "data": entity,
                "timestamp": payload.get("timestamp"),
            })
            await self._broadcast_update("entities", entity)
    
    async def _handle_entity_merged(self, payload: EventPayload):
        """Handle entity merge events."""
        kept_entity = payload.get("kept_entity")
        merged_entities = payload.get("merged_entities", [])
        
        if kept_entity:
            update = {
                "type": "entity_merged",
                "kept_entity": kept_entity,
                "merged_entities": merged_entities,
                "timestamp": payload.get("timestamp"),
            }
            await self._broadcast_update("entities", update)
    
    async def _broadcast_update(self, stream_type: str, data: Any):
        """Broadcast an update to all active stream subscribers."""
        update = {
            "stream_type": stream_type,
            "data": data,
            "timestamp": time.time(),
        }
        
        # Send to all active stream queues
        for stream_id, queue in list(self._active_streams.items()):
            try:
                queue.put_nowait(update)
            except asyncio.QueueFull:
                logger.warning(f"Stream queue {stream_id} is full, dropping update")
            except Exception as e:
                logger.error(f"Error broadcasting to stream {stream_id}: {e}")
    
    def create_stream(self, stream_types: Optional[list[str]] = None) -> str:
        """Create a new intelligence stream.
        
        Args:
            stream_types: List of stream types to subscribe to (None = all)
            
        Returns:
            Stream ID for tracking
        """
        import uuid
        stream_id = f"stream_{uuid.uuid4().hex[:8]}"
        
        self._active_streams[stream_id] = asyncio.Queue(maxsize=100)
        
        logger.info(f"Created intelligence stream {stream_id}")
        return stream_id
    
    async def get_stream_updates(self, stream_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Get updates from a stream.
        
        Args:
            stream_id: Stream ID returned by create_stream
            
        Yields:
            Stream update dictionaries
        """
        queue = self._active_streams.get(stream_id)
        if not queue:
            raise ValueError(f"Stream {stream_id} not found")
        
        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield update
            except asyncio.TimeoutError:
                # Yield heartbeat to keep connection alive
                yield {"type": "heartbeat", "timestamp": time.time()}
            except Exception as e:
                logger.error(f"Error in stream {stream_id}: {e}")
                break
    
    def close_stream(self, stream_id: str):
        """Close a stream.
        
        Args:
            stream_id: Stream ID to close
        """
        if stream_id in self._active_streams:
            del self._active_streams[stream_id]
            logger.info(f"Closed intelligence stream {stream_id}")
    
    def get_stream_history(self, stream_type: str, limit: int = 10) -> list[Dict[str, Any]]:
        """Get recent history from a stream buffer.
        
        Args:
            stream_type: Type of stream (semantic_profiles, narratives, etc.)
            limit: Maximum number of items to return
            
        Returns:
            List of recent stream items
        """
        buffer = self._stream_buffers.get(stream_type)
        if not buffer:
            return []
        
        return list(buffer)[-limit:]
