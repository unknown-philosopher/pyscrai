"""PyScrAI Forge - Main application entry point."""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path

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
from forge.domain.graph.advanced_analyzer import AdvancedGraphAnalysisService
from forge.infrastructure.llm.provider_factory import ProviderFactory
import duckdb

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)



async def init_services(controller: AppController) -> None:
    """Initialize all services asynchronously."""
    # Start the controller (wire event bus subscriptions)
    await controller.start()
    logger.info("AppController started")

    # Initialize LLM provider early (needed for extraction and intelligence services)
    try:
        llm_provider, _ = ProviderFactory.create_from_env()
        logger.info("LLM provider initialized")
    except Exception as e:
        logger.warning(f"Could not initialize LLM provider from environment: {e}")
        logger.warning("Some services may not function correctly without LLM provider")
        llm_provider = None

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

    # Initialize and start SemanticProfilerService (requires LLM provider)
    if llm_provider:
        profiler_service = SemanticProfilerService(
            controller.bus,
            llm_provider,
            db_connection
        )
        await profiler_service.start()
        logger.info("SemanticProfilerService started")
    else:
        logger.warning("SemanticProfilerService not started: LLM provider unavailable")

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
    shell_view = build_shell(page, controller)
    page.views.append(shell_view)
    # View is already added, no need for route navigation

    logger.info("Application initialized successfully")


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)
