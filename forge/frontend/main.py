"""
Forge Frontend Entry Point.

Launches the NiceGUI application in native desktop mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import app, ui

from forge.frontend.state import get_session
from forge.frontend.theme import create_layout
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState

logger = get_logger("frontend.main")


def setup_routes() -> None:
    """Register all UI page routes."""
    from forge.frontend.pages import (
        anvil,
        dashboard,
        geoint,
        humint,
        landing,
        osint,
        sigint,
        synth,
    )
    
    # Landing page (project selection)
    @ui.page("/")
    def index_page() -> None:
        create_layout(landing.content, active_page="landing")
    
    # Dashboard (overview)
    @ui.page("/dashboard")
    def dashboard_page() -> None:
        create_layout(dashboard.content, active_page="dashboard")
    
    # Phase 0: OSINT (Extraction)
    @ui.page("/osint")
    def osint_page() -> None:
        create_layout(osint.content, active_page="osint")
    
    # Phase 1: HUMINT (Entities)
    @ui.page("/humint")
    def humint_page() -> None:
        create_layout(humint.content, active_page="humint")
    
    # Phase 2: SIGINT (Relationships)
    @ui.page("/sigint")
    def sigint_page() -> None:
        create_layout(sigint.content, active_page="sigint")
    
    # Phase 3: SYNTH (Narrative)
    @ui.page("/synth")
    def synth_page() -> None:
        create_layout(synth.content, active_page="synth")
    
    # Phase 4: GEOINT (Cartography)
    @ui.page("/geoint")
    def geoint_page() -> None:
        create_layout(geoint.content, active_page="geoint")
    
    # Phase 5: ANVIL (Finalize)
    @ui.page("/anvil")
    def anvil_page() -> None:
        create_layout(anvil.content, active_page="anvil")


def launch_ui(state: "ForgeState | None" = None) -> int:
    """Launch the Forge UI in native desktop mode.
    
    Args:
        state: Optional pre-initialized ForgeState. If None, one will be created.
        
    Returns:
        Exit code (0 for success)
    """
    from forge.frontend.state import initialize_session
    
    logger.info("Launching Forge UI in native mode")
    
    # Initialize the session state
    if state:
        initialize_session(state)
    
    # Set up page routes
    setup_routes()
    
    # Configure app settings
    app.native.window_args["text_select"] = True
    
    # Run in native mode
    ui.run(
        native=True,
        title="PyScrAI | Forge 3.0",
        dark=True,
        reload=False,
        window_size=(1400, 900),
        fullscreen=False,
    )
    
    logger.info("Forge UI closed")
    return 0


if __name__ == "__main__":
    # Direct launch for development
    launch_ui()
