"""Ingest controller for document processing."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import flet as ft

from forge.core import events

if TYPE_CHECKING:
    from forge.core.app_controller import AppController

logger = logging.getLogger(__name__)


class IngestController:
    """Handles document ingestion UI and event publishing."""
    
    def __init__(self, app_controller: AppController, page: ft.Page):
        self.app_controller = app_controller
        self.page = page
        self._doc_counter = 0
    
    def build_view(self) -> ft.Control:
        """Build the ingest view with text input and controls."""
        
        # Document text input
        doc_input = ft.TextField(
            label="Document Text",
            hint_text="Paste or type document content here...",
            multiline=True,
            min_lines=15,
            max_lines=20,
            expand=True,
            bgcolor="rgba(255, 255, 255, 0.05)",
            color=ft.Colors.WHITE,
            border_color="rgba(100, 200, 255, 0.3)",
            focused_border_color="rgba(100, 200, 255, 0.8)",
        )
        
        # Status text
        status = ft.Text(
            "Ready to process documents",
            color=ft.Colors.CYAN_200,
            size=14,
        )
        
        # Process button
        async def on_process_click(e):
            """Handle process button click."""
            text = doc_input.value
            
            if not text or not text.strip():
                status.value = "⚠️  Please enter document text"
                status.color = ft.Colors.ORANGE_300
                self.page.update()
                return
            
            # Update UI
            status.value = "🔄 Processing document..."
            status.color = ft.Colors.CYAN_300
            process_btn.disabled = True
            self.page.update()
            
            # Generate document ID
            self._doc_counter += 1
            doc_id = f"doc_{self._doc_counter:04d}"
            
            try:
                # Publish to event bus
                logger.info(f"Publishing document {doc_id} to event bus")
                await self.app_controller.publish(
                    events.TOPIC_DATA_INGESTED,
                    events.create_data_ingested_event(doc_id, text.strip())
                )
                
                # Update UI
                status.value = f"✅ Document {doc_id} processed! Check workspace for intelligence."
                status.color = ft.Colors.GREEN_300
                
                # Clear input
                doc_input.value = ""
                
                # Log to AG-UI feed
                await self.app_controller.push_agui_log(
                    f"Document {doc_id} ingested ({len(text)} chars)",
                    "info"
                )
                
            except Exception as ex:
                logger.error(f"Error processing document: {ex}")
                status.value = f"❌ Error: {str(ex)}"
                status.color = ft.Colors.RED_300
                
                await self.app_controller.push_agui_log(
                    f"Error processing document: {str(ex)}",
                    "error"
                )
            
            finally:
                process_btn.disabled = False
                self.page.update()
        
        process_btn = ft.ElevatedButton(
            "Process Document",
            icon=ft.Icons.ROCKET_LAUNCH,
            on_click=lambda e: asyncio.create_task(on_process_click(e)),
            bgcolor=ft.Colors.CYAN_700,
            color=ft.Colors.WHITE,
            width=200,
        )
        
        # Clear button
        def on_clear_click(e):
            """Handle clear button click."""
            doc_input.value = ""
            status.value = "Ready to process documents"
            status.color = ft.Colors.CYAN_200
            self.page.update()
        
        clear_btn = ft.OutlinedButton(
            "Clear",
            icon=ft.Icons.CLEAR,
            on_click=on_clear_click,
            width=120,
        )
        
        # Example templates
        examples = [
            {
                "title": "Person & Organization",
                "text": """Alice Smith is a software engineer at TechCorp. She works closely with Bob Jones, the senior architect. Together they built the PyScrAI system for document analysis. Alice specializes in AI and machine learning. Bob has 15 years of experience in distributed systems."""
            },
            {
                "title": "Business Meeting",
                "text": """The quarterly business review was attended by Sarah Chen (CEO), Michael Rodriguez (CFO), and Jennifer Park (CTO). They discussed expanding operations to the Seattle office and hiring 20 new engineers. The company's revenue grew 45% this quarter, primarily driven by the new cloud platform."""
            },
            {
                "title": "Research Paper",
                "text": """Dr. Elena Petrova from MIT collaborated with Prof. James Wilson at Stanford to develop a novel neural architecture. Their research, published in Nature, demonstrates significant improvements in natural language understanding. The work was funded by NSF grant #12345."""
            }
        ]
        
        def load_example(text: str):
            """Load example text into input."""
            def handler(e):
                doc_input.value = text
                status.value = "Example loaded - click Process to analyze"
                status.color = ft.Colors.CYAN_200
                self.page.update()
            return handler
        
        example_buttons = [
            ft.OutlinedButton(
                ex["title"],
                icon=ft.Icons.FILE_COPY,
                on_click=load_example(ex["text"]),
                tooltip=ex["text"][:100] + "..."
            )
            for ex in examples
        ]
        
        # Layout
        return ft.Container(
            expand=True,
            padding=20,
            content=ft.Column(
                [
                    # Header
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.UPLOAD_FILE, size=32, color=ft.Colors.CYAN_300),
                            ft.Text(
                                "Document Ingest",
                                size=24,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=12,
                    ),
                    
                    ft.Divider(color="rgba(255, 255, 255, 0.1)", height=20),
                    
                    # Instructions
                    ft.Container(
                        bgcolor="rgba(100, 200, 255, 0.1)",
                        padding=12,
                        border_radius=8,
                        content=ft.Column(
                            [
                                ft.Text(
                                    "📝 How to use:",
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.CYAN_100,
                                ),
                                ft.Text(
                                    "1. Paste or type document text below",
                                    color=ft.Colors.WHITE70,
                                    size=12,
                                ),
                                ft.Text(
                                    "2. Click 'Process Document' to extract entities and generate intelligence",
                                    color=ft.Colors.WHITE70,
                                    size=12,
                                ),
                                ft.Text(
                                    "3. View results in the workspace panel (center) and AG-UI feed (right)",
                                    color=ft.Colors.WHITE70,
                                    size=12,
                                ),
                            ],
                            spacing=4,
                        ),
                    ),
                    
                    ft.Container(height=12),
                    
                    # Example templates
                    ft.Row(
                        [
                            ft.Text("Quick Examples:", color=ft.Colors.WHITE70, size=12),
                            *example_buttons,
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    
                    ft.Container(height=8),
                    
                    # Input area
                    doc_input,
                    
                    ft.Container(height=12),
                    
                    # Actions
                    ft.Row(
                        [
                            process_btn,
                            clear_btn,
                            ft.Container(expand=True),
                            status,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
