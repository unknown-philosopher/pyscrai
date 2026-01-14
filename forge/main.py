"""PyScrAI Forge - Main application entry point."""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import threading
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

import flet as ft
from forge.core.app_controller import AppController
from forge.presentation.layouts.shell import build_shell
from forge.domain.extraction.service import DocumentExtractionService
from forge.domain.resolution.service import EntityResolutionService
from forge.domain.graph.service import GraphAnalysisService
from forge.infrastructure.persistence.duckdb_service import DuckDBPersistenceService
from forge.infrastructure.embeddings.embedding_service import EmbeddingService
from forge.infrastructure.vector.qdrant_service import QdrantService
from forge.domain.resolution.deduplication_service import DeduplicationService
from forge.domain.intelligence.semantic_profiler import SemanticProfilerService
from forge.domain.intelligence.narrative_service import NarrativeSynthesisService
from forge.domain.intelligence.streaming_service import IntelligenceStreamingService
from forge.domain.graph.advanced_analyzer import AdvancedGraphAnalysisService
from forge.domain.interaction.workflow_service import UserInteractionWorkflowService
from forge.infrastructure.export.export_service import ExportService
from forge.infrastructure.llm.provider_factory import ProviderFactory
from forge.presentation.renderer import set_event_bus
from forge.domain.session.session_manager import SessionManager
from forge.core.service_registry import set_session_manager
import duckdb

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configure comprehensive logging
# File handler: Log everything (DEBUG level) to /home/tyler/_development/pyscrai/data/pyscrai.log
# Console handler: Only log WARNING and ERROR to terminal
log_file_path = Path("/home/tyler/_development/pyscrai/data/pyscrai.log")
log_file_path.parent.mkdir(parents=True, exist_ok=True)

# Create root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Remove existing handlers to avoid duplicates
root_logger.handlers.clear()

# File handler - comprehensive logging (all levels)
file_handler = logging.handlers.RotatingFileHandler(
    log_file_path,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)

# Console handler - only warnings and errors
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # Only WARNING and ERROR
console_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)

# Suppress verbose third-party library logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured: file={log_file_path}, console=WARNING+")


async def init_services(controller: AppController) -> None:
    """Initialize all services asynchronously."""
    
    # Start the controller (wire event bus subscriptions)
    await controller.start()
    logger.info("AppController started")

    # Initialize primary LLM provider early (needed for extraction and intelligence services)
    try:
        llm_provider, _ = ProviderFactory.create_from_env()
        logger.info("Primary LLM provider initialized")
    except Exception as e:
        logger.warning(f"Could not initialize primary LLM provider from environment: {e}")
        logger.warning("Some services may not function correctly without LLM provider")
        llm_provider = None
    
    # Initialize semantic LLM provider (for semantic profiling)
    try:
        semantic_llm_provider, _ = ProviderFactory.create_semantic_provider_from_env()
        logger.info("Semantic LLM provider initialized")
    except Exception as e:
        logger.warning(f"Could not initialize semantic LLM provider from environment: {e}")
        logger.warning("SemanticProfilerService will use primary provider if available")
        semantic_llm_provider = llm_provider  # Fall back to primary provider

    # Initialize and start DocumentExtractionService (needs LLM provider)
    extraction_service = DocumentExtractionService(controller.bus, llm_provider)
    await extraction_service.start()
    logger.info("DocumentExtractionService started")

    # Initialize and start EntityResolutionService (needs LLM provider)
    resolution_service = EntityResolutionService(controller.bus, llm_provider)
    await resolution_service.start()
    logger.info("EntityResolutionService started")

    # Initialize and start GraphAnalysisService
    graph_service = GraphAnalysisService(controller.bus)
    await graph_service.start()
    logger.info("GraphAnalysisService started")

    # Initialize and start DuckDBPersistenceService
    persistence_service = DuckDBPersistenceService(controller.bus)
    await persistence_service.start()
    logger.info("DuckDBPersistenceService started")

    # Initialize and start EmbeddingService
    embedding_service = EmbeddingService(controller.bus)
    await embedding_service.start()
    logger.info("EmbeddingService started")

    # Initialize and start QdrantService
    qdrant_service = QdrantService(controller.bus)
    await qdrant_service.start()
    logger.info("QdrantService started")

    # Open DuckDB connection for intelligence services
    db_connection = duckdb.connect(persistence_service.db_path)
    logger.info(f"Database connection opened: {persistence_service.db_path}")

    # Initialize and start DeduplicationService (requires LLM provider)
    if llm_provider:
        deduplication_service = DeduplicationService(
            controller.bus,
            qdrant_service,
            llm_provider,
            db_connection
        )
        await deduplication_service.start()
        logger.info("DeduplicationService started")
    else:
        logger.warning("DeduplicationService not started: LLM provider unavailable")

    # Initialize and start SemanticProfilerService (uses semantic LLM provider)
    if semantic_llm_provider:
        profiler_service = SemanticProfilerService(
            controller.bus,
            semantic_llm_provider,
            db_connection
        )
        await profiler_service.start()
        logger.info("SemanticProfilerService started with semantic provider")
    elif llm_provider:
        # Fall back to primary provider if semantic provider not available
        profiler_service = SemanticProfilerService(
            controller.bus,
            llm_provider,
            db_connection
        )
        await profiler_service.start()
        logger.info("SemanticProfilerService started with primary provider (semantic provider unavailable)")
    else:
        logger.warning("SemanticProfilerService not started: No LLM provider available")

    # Initialize and start NarrativeSynthesisService (requires LLM provider)
    if llm_provider:
        narrative_service = NarrativeSynthesisService(
            controller.bus,
            llm_provider,
            db_connection
        )
        await narrative_service.start()
        logger.info("NarrativeSynthesisService started")
    else:
        logger.warning("NarrativeSynthesisService not started: LLM provider unavailable")

    # Initialize and start AdvancedGraphAnalysisService (requires LLM provider)
    if llm_provider:
        advanced_graph_service = AdvancedGraphAnalysisService(
            controller.bus,
            llm_provider,
            db_connection
        )
        await advanced_graph_service.start()
        logger.info("AdvancedGraphAnalysisService started")
    else:
        logger.warning("AdvancedGraphAnalysisService not started: LLM provider unavailable")
    
    # Initialize and start UserInteractionWorkflowService
    workflow_service = UserInteractionWorkflowService(controller.bus)
    await workflow_service.start()
    logger.info("UserInteractionWorkflowService started")
    
    # Initialize and start IntelligenceStreamingService
    streaming_service = IntelligenceStreamingService(controller.bus)
    await streaming_service.start()
    logger.info("IntelligenceStreamingService started")
    
    # Initialize ExportService (no async start needed)
    export_service = ExportService(db_connection)
    logger.info("ExportService initialized")
    
    # Set event bus in renderer for component actions
    set_event_bus(controller.bus)
    logger.info("Event bus set in renderer")
    
    # Initialize SessionManager but DO NOT auto-restore
    session_manager = SessionManager(
        controller, 
        persistence_service, 
        qdrant_service, 
        embedding_service
    )
    set_session_manager(session_manager)
    logger.info("Session Manager initialized (Ready for manual restore)")


def _run_async_init(controller: AppController) -> None:
    """Run async initialization in a separate thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_services(controller))
        # Keep the loop running for background tasks
        loop.run_forever()
    except Exception as e:
        logger.error(f"Error in async initialization: {e}")
    finally:
        loop.close()


def main(page: ft.Page) -> None:
    """Main Flet application entry point."""
    logger.info("Initializing PyScrAI Forge...")

    # Hide the top bar and make the window frameless/transparent
    page.window.title_bar_hidden = False
    # page.window.title = "PyScrAI - Tyler Hamilton"
    page.window.bgcolor = ft.Colors.TRANSPARENT  # Use capital 'C'
    page.bgcolor = ft.Colors.TRANSPARENT         # Use capital 'C'

    # Initialize the application controller
    controller = AppController()

    # Start services asynchronously in a background thread
    # This allows the UI to render immediately while services initialize
    init_thread = threading.Thread(
        target=_run_async_init,
        args=(controller,),
        daemon=True,
        name="ServiceInitThread",
    )
    init_thread.start()

    # Build the shell UI immediately
    # SessionManager will be initialized in background thread and accessed via registry
    shell_view = build_shell(page, controller)
    page.views.append(shell_view)
    # View is already added, no need for route navigation

    logger.info("Application initialized successfully")


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)
