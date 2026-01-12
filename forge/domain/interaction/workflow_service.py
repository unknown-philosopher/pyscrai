"""User Interaction Workflow Service for PyScrAI Forge.

Handles user approvals, corrections, and other interactive workflows.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Status of a workflow."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"
    EXPIRED = "expired"


@dataclass
class WorkflowRequest:
    """Represents a workflow request awaiting user action."""
    workflow_id: str
    workflow_type: str  # "approval", "correction", "confirmation"
    title: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    callback: Optional[Callable[[WorkflowStatus, Dict[str, Any]], Awaitable[None]]] = None
    timeout: Optional[float] = None  # Seconds until expiration
    created_at: float = field(default_factory=time.time)


class UserInteractionWorkflowService:
    """Service for managing user interaction workflows (approvals, corrections, etc.)."""
    
    def __init__(self, event_bus: EventBus):
        """Initialize the workflow service.
        
        Args:
            event_bus: Event bus for publishing workflow requests and handling responses
        """
        self.event_bus = event_bus
        self.service_name = "UserInteractionWorkflowService"
        
        # Active workflows awaiting user response
        self._active_workflows: Dict[str, WorkflowRequest] = {}
        
        # Workflow ID counter
        self._workflow_counter = 0
        
    async def start(self):
        """Start the service and subscribe to events."""
        logger.info("Starting UserInteractionWorkflowService")
        
        # Subscribe to user action events
        await self.event_bus.subscribe(events.TOPIC_USER_ACTION, self._handle_user_action)
        
        # Start background task to expire old workflows
        asyncio.create_task(self._expire_workflows_loop())
        
        logger.info("UserInteractionWorkflowService started")
    
    async def request_approval(
        self,
        title: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[bool, Dict[str, Any]], Awaitable[None]]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Request user approval for an action.
        
        Args:
            title: Title of the approval request
            message: Message describing what needs approval
            context: Additional context data
            callback: Async callback function(status: bool, context: dict) -> None
            timeout: Optional timeout in seconds
            
        Returns:
            Workflow ID for tracking
        """
        workflow_id = f"approval_{self._workflow_counter}"
        self._workflow_counter += 1
        
        async def approval_callback(status: WorkflowStatus, ctx: Dict[str, Any]) -> None:
            if callback:
                approved = status == WorkflowStatus.APPROVED
                await callback(approved, ctx)
        
        workflow = WorkflowRequest(
            workflow_id=workflow_id,
            workflow_type="approval",
            title=title,
            message=message,
            context=context or {},
            callback=approval_callback,
            timeout=timeout,
        )
        
        self._active_workflows[workflow_id] = workflow
        
        # Publish workflow request to AG-UI feed
        await self._publish_workflow_request(workflow)
        
        return workflow_id
    
    async def request_correction(
        self,
        title: str,
        message: str,
        current_value: Any,
        context: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[Any, Dict[str, Any]], Awaitable[None]]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Request user correction for a value.
        
        Args:
            title: Title of the correction request
            message: Message describing what needs correction
            current_value: Current value that can be corrected
            context: Additional context data
            callback: Async callback function(corrected_value: Any, context: dict) -> None
            timeout: Optional timeout in seconds
            
        Returns:
            Workflow ID for tracking
        """
        workflow_id = f"correction_{self._workflow_counter}"
        self._workflow_counter += 1
        
        async def correction_callback(status: WorkflowStatus, ctx: Dict[str, Any]) -> None:
            if callback:
                corrected_value = ctx.get("corrected_value", current_value)
                await callback(corrected_value, ctx)
        
        workflow = WorkflowRequest(
            workflow_id=workflow_id,
            workflow_type="correction",
            title=title,
            message=message,
            context={**(context or {}), "current_value": current_value},
            callback=correction_callback,
            timeout=timeout,
        )
        
        self._active_workflows[workflow_id] = workflow
        
        # Publish workflow request to AG-UI feed
        await self._publish_workflow_request(workflow)
        
        return workflow_id
    
    async def _publish_workflow_request(self, workflow: WorkflowRequest):
        """Publish a workflow request to the AG-UI feed."""
        # Create a schema for the workflow request
        if workflow.workflow_type == "approval":
            schema = {
                "type": "card",
                "title": workflow.title,
                "summary": workflow.message,
                "props": {
                    "workflow_id": workflow.workflow_id,
                    "workflow_type": workflow.workflow_type,
                    "actions": [
                        {
                            "type": "button",
                            "props": {
                                "label": "Approve",
                                "action": f"workflow.approve.{workflow.workflow_id}",
                                "variant": "primary",
                            }
                        },
                        {
                            "type": "button",
                            "props": {
                                "label": "Reject",
                                "action": f"workflow.reject.{workflow.workflow_id}",
                                "variant": "danger",
                            }
                        }
                    ]
                }
            }
        elif workflow.workflow_type == "correction":
            schema = {
                "type": "form",
                "title": workflow.title,
                "props": {
                    "workflow_id": workflow.workflow_id,
                    "workflow_type": workflow.workflow_type,
                    "message": workflow.message,
                    "fields": [
                        {
                            "type": "input",
                            "props": {
                                "label": "Corrected Value",
                                "placeholder": str(workflow.context.get("current_value", "")),
                                "value": str(workflow.context.get("current_value", "")),
                                "required": True,
                            }
                        }
                    ],
                    "submit_label": "Submit Correction",
                    "submit_action": f"workflow.correct.{workflow.workflow_id}",
                }
            }
        else:
            # Generic workflow
            schema = {
                "type": "card",
                "title": workflow.title,
                "summary": workflow.message,
                "props": {
                    "workflow_id": workflow.workflow_id,
                    "workflow_type": workflow.workflow_type,
                }
            }
        
        # Publish to workspace
        await self.event_bus.publish(
            events.TOPIC_WORKSPACE_SCHEMA,
            events.create_workspace_schema_event(schema)
        )
        
        # Also log to AG-UI feed
        await self.event_bus.publish(
            events.TOPIC_AGUI_EVENT,
            events.create_agui_event(
                f"Workflow Request: {workflow.title}",
                level="info",
                topic=workflow.workflow_type,
            )
        )
    
    async def _handle_user_action(self, payload: EventPayload):
        """Handle user action events."""
        action = payload.get("action", "")
        
        if action.startswith("workflow.approve."):
            workflow_id = action.replace("workflow.approve.", "")
            await self._resolve_workflow(workflow_id, WorkflowStatus.APPROVED, payload)
        elif action.startswith("workflow.reject."):
            workflow_id = action.replace("workflow.reject.", "")
            await self._resolve_workflow(workflow_id, WorkflowStatus.REJECTED, payload)
        elif action.startswith("workflow.correct."):
            workflow_id = action.replace("workflow.correct.", "")
            corrected_value = payload.get("corrected_value") or payload.get("value")
            await self._resolve_workflow(
                workflow_id,
                WorkflowStatus.CORRECTED,
                {**payload, "corrected_value": corrected_value}
            )
    
    async def _resolve_workflow(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        result_data: Dict[str, Any]
    ):
        """Resolve a workflow with a status."""
        workflow = self._active_workflows.get(workflow_id)
        if not workflow:
            logger.warning(f"Workflow {workflow_id} not found")
            return
        
        workflow.status = status
        
        # Call callback if provided
        if workflow.callback:
            try:
                await workflow.callback(status, {**workflow.context, **result_data})
            except Exception as e:
                logger.error(f"Error in workflow callback for {workflow_id}: {e}")
        
        # Remove from active workflows
        del self._active_workflows[workflow_id]
        
        # Log resolution
        await self.event_bus.publish(
            events.TOPIC_AGUI_EVENT,
            events.create_agui_event(
                f"Workflow {workflow_id} {status.value}",
                level="info",
                topic="workflow",
            )
        )
    
    async def _expire_workflows_loop(self):
        """Background task to expire old workflows."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                current_time = time.time()
                expired_workflows = []
                
                for workflow_id, workflow in self._active_workflows.items():
                    if workflow.timeout and (current_time - workflow.created_at) > workflow.timeout:
                        expired_workflows.append(workflow_id)
                
                for workflow_id in expired_workflows:
                    workflow = self._active_workflows[workflow_id]
                    workflow.status = WorkflowStatus.EXPIRED
                    
                    if workflow.callback:
                        try:
                            await workflow.callback(WorkflowStatus.EXPIRED, workflow.context)
                        except Exception as e:
                            logger.error(f"Error in expired workflow callback for {workflow_id}: {e}")
                    
                    del self._active_workflows[workflow_id]
                    
                    logger.info(f"Workflow {workflow_id} expired")
                    
            except Exception as e:
                logger.error(f"Error in workflow expiration loop: {e}")
