"""
AI Assistant Chat Panel.

Terminal-style chat interface that routes through UserProxyAgent.
Intelligence platform aesthetic with monospace fonts and minimal styling.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from nicegui import ui

from forge.legacy_nicegui.state import get_session, get_ui_context
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.agents.user_proxy import UserProxyAgent

logger = get_logger("frontend.assistant")


@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # "user" or "assistant" or "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    action_taken: str | None = None


class AssistantPanel:
    """Terminal-style AI Assistant panel."""
    
    def __init__(self) -> None:
        self.messages: list[ChatMessage] = []
        self.input_text: str = ""
        self._agent: "UserProxyAgent | None" = None
        self._processing: bool = False
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the terminal-style assistant panel."""
        with ui.column().classes("w-full h-full").style("background: #0a0a0a;"):
            # Header
            with ui.row().classes("w-full items-center justify-between p-3").style(
                "background: #111; border-bottom: 1px solid #333;"
            ):
                ui.html('<span class="mono" style="color: #e0e0e0; font-size: 0.9rem; font-weight: 500;">ASSISTANT_V2.0</span>', sanitize=False)
                # Toggle button removed - now handled by drawer header in theme.py
            
            # Terminal output area
            with ui.scroll_area().classes("flex-grow w-full").style(
                "background: #0a0a0a;"
            ) as self._chat_area:
                with ui.column().classes("w-full p-3 gap-2") as self._messages_container:
                    self._render_init_messages()
            
            # Status bar
            with ui.row().classes("w-full items-center justify-between px-3 py-2").style(
                "background: #0d0d0d; border-top: 1px solid #222;"
            ):
                ui.html('<span class="mono" style="color: #555; font-size: 0.65rem;">LLM: CLAUDE-3-OPUS</span>', sanitize=False)
                ui.html('<span class="mono" style="color: #555; font-size: 0.65rem;">LATENCY: 45MS</span>', sanitize=False)
            
            # Input area
            with ui.row().classes("w-full items-center p-3 gap-2").style(
                "background: #111; border-top: 1px solid #333;"
            ):
                ui.html('<span class="mono" style="color: #00b8d4; font-size: 0.9rem;">&gt;</span>', sanitize=False)
                self._input = ui.input(
                    placeholder="Enter command..."
                ).classes("flex-grow").props("borderless dense dark input-class=mono").style(
                    "background: transparent !important; color: #e0e0e0 !important; font-family: 'JetBrains Mono', monospace !important;"
                )
                self._input.on("keydown.enter", self._on_submit)
                
                with ui.element("div").classes("px-3 py-1 cursor-pointer rounded").style(
                    "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;"
                ).on("click", self._on_submit) as self._send_btn:
                    ui.html('SEND', sanitize=False)
    
    def _render_init_messages(self) -> None:
        """Show initial system boot messages."""
        boot_messages = [
            ("SYSTEM_INIT:", "#555"),
            ("Loading modules... OK.", "#555"),
            ("Connecting to secure server... OK.", "#555"),
            ("Assistant Ready.", "#555"),
            ("", ""),
            ("[" + datetime.now().strftime("%H:%M:%S") + "] User connected.", "#666"),
        ]
        
        with self._messages_container:
            for msg, color in boot_messages:
                if msg:
                    ui.html(f'<span class="mono" style="color: {color}; font-size: 0.8rem; line-height: 1.6;">{msg}</span>', sanitize=False)
            
            # Welcome message from AI
            ui.html('<div style="margin-top: 12px;"></div>', sanitize=False)
            ui.html('<span class="mono" style="color: #00b8d4; font-size: 0.8rem;">AI_CORE &gt;</span>', sanitize=False)
            ui.html('''<span class="mono" style="color: #aaa; font-size: 0.8rem; line-height: 1.6; display: block; margin-top: 4px;">
                Hello. I am ready to assist with entity extraction, relationship mapping, and OSINT analysis. What is your directive?
            </span>''', sanitize=False)
            
            # Quick action buttons
            with ui.row().classes("gap-2 mt-3"):
                for label in ["ANALYZE ENTITIES", "MAP NETWORK"]:
                    ui.html(f'<span class="mono forge-btn px-2 py-1" style="font-size: 0.65rem; cursor: pointer;">{label}</span>', sanitize=False)
    
    def _add_message(self, role: str, content: str, action: str | None = None) -> None:
        """Add a message to the terminal output."""
        msg = ChatMessage(role=role, content=content, action_taken=action)
        self.messages.append(msg)
        
        with self._messages_container:
            ui.html('<div style="margin-top: 12px;"></div>', sanitize=False)
            
            if role == "user":
                ui.html(f'<span class="mono" style="color: #ffab00; font-size: 0.8rem;">&lt; OPERATOR</span>', sanitize=False)
                ui.html(f'<span class="mono" style="color: #e0e0e0; font-size: 0.8rem; display: block; margin-top: 4px; margin-left: 16px;">{content}</span>', sanitize=False)
            else:
                ui.html('<span class="mono" style="color: #00b8d4; font-size: 0.8rem;">AI_CORE &gt;</span>', sanitize=False)
                if self._processing:
                    ui.html('<span class="mono" style="color: #555; font-size: 0.8rem; display: block; margin-top: 4px;">Processing...</span>', sanitize=False)
                else:
                    ui.html(f'<span class="mono" style="color: #aaa; font-size: 0.8rem; line-height: 1.6; display: block; margin-top: 4px;">{content}</span>', sanitize=False)
                    if action:
                        ui.html(f'<span class="mono" style="color: #00c853; font-size: 0.7rem; display: block; margin-top: 4px;">[ACTION: {action}]</span>', sanitize=False)
        
        # Scroll to bottom
        self._chat_area.scroll_to(percent=1.0)
    
    async def _process_message(self, text: str) -> None:
        """Process a user message through UserProxyAgent."""
        self._processing = True
        
        try:
            # Get or create the agent
            if self._agent is None:
                from forge.agents.user_proxy import UserProxyAgent
                session = get_session()
                self._agent = UserProxyAgent(llm_provider=session.llm)
            
            # Get context
            ctx = get_ui_context()
            
            # Process through agent
            response = await self._agent.process(
                user_input=text,
                active_page=ctx.get("active_page", "dashboard"),
                selected_entities=ctx.get("selected_entities", []),
            )
            
            # Display response
            self._add_message(
                role="assistant",
                content=response.message,
                action=response.action_taken,
            )
            
        except Exception as e:
            logger.error(f"Assistant error: {e}")
            self._add_message(
                role="assistant",
                content=f"❌ Error: {str(e)}",
            )
        finally:
            self._processing = False
            self._send_btn.props(remove="loading")
    
    async def _on_submit(self) -> None:
        """Handle message submission."""
        text = self._input.value.strip()
        if not text or self._processing:
            return
        
        # Clear input
        self._input.value = ""
        
        # Add user message
        self._add_message(role="user", content=text)
        
        # Update context
        self._update_context_badge()
        
        # Process asynchronously
        await self._process_message(text)
