"""PyScrAI Forge - Main application entry point."""

from __future__ import annotations

import asyncio
import logging
import threading

import flet as ft

from forge.core.app_controller import AppController
from forge.presentation.layouts.shell import build_shell

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
