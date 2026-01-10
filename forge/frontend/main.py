"""
Forge Frontend Entry Point - Flet Native Edition.

Tactical "Cockpit" interface entry point.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from forge.app.state import ForgeState, init_state
from forge.frontend import style
from forge.frontend.components.app_shell import AppShell
from forge.frontend.state import FletXState, init_fletx_state
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.config import ForgeConfig

logger = get_logger("frontend.main")


# Global shell instance for view routing
_shell: AppShell | None = None


def main(page: ft.Page) -> None:
    """Main Flet entry point.
    
    Args:
        page: Flet page instance
    """
    global _shell
    
    logger.info("Initializing Forge Frontend (Flet)")
    
    # 1. Configure page (Flet 0.80+ uses page.window.* instead of page.window_*)
    page.title = "PyScrAI | Forge 3.0"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 1400
    page.window.height = 900
    page.window.min_width = 1200
    page.window.min_height = 700
    
    # 2. Initialize backend state
    try:
        forge_state = init_state()
        logger.info(f"ForgeState initialized (session: {forge_state.session_id})")
    except Exception as e:
        logger.error(f"Failed to initialize ForgeState: {e}")
        # Create a fallback state if needed
        from forge.app.config import get_config
        config = get_config()
        forge_state = init_state(config)
    
    # 3. Initialize FletX state wrapper
    try:
        fletx_state = init_fletx_state(page, forge_state)
        logger.info("FletX state initialized")
    except Exception as e:
        logger.error(f"Failed to initialize FletX state: {e}")
        raise
    
    # 4. Build app shell (route handler needs shell reference)
    try:
        _shell = AppShell(page, fletx_state)
        logger.info("App shell initialized")
    except Exception as e:
        logger.error(f"Failed to initialize app shell: {e}")
        raise
    
    # 5. Setup view routing (after shell is created so route handler can access it)
    _setup_route_handler(page, fletx_state)
    
    # 6. Initial route - explicitly load landing view
    # page.go("/") may not trigger if already at "/", so load directly
    try:
        from forge.frontend.views import landing
        view_content = landing.render_landing_view(fletx_state)
        _shell.set_view_content(view_content)
        logger.debug("Initial landing view loaded")
    except Exception as e:
        logger.error(f"Failed to load initial landing view: {e}")
    
    logger.info("Forge Frontend ready")


def _setup_route_handler(page: ft.Page, state: FletXState) -> None:
    """Setup view routing for all pages.
    
    This is the SINGLE route handler that handles all route changes.
    It updates shell state and loads the appropriate view.
    
    Args:
        page: Flet page instance
        state: FletXState instance
    """
    def route_handler(route: ft.RouteChangeEvent) -> None:
        """Handle route changes and load appropriate view."""
        global _shell
        
        if _shell is None:
            # Shell not ready yet, skip
            logger.warning("Shell not ready, skipping route change")
            return
        
        route_path = route.route if route.route else "/"
        
        logger.debug(f"Route change: {route_path}")
        
        # Update shell internal state
        _shell._on_route_change(route)
        
        try:
            from forge.frontend.views import (
                anvil,
                dashboard,
                geoint,
                humint,
                landing,
                osint,
                sigint,
                synth,
            )
            
            # Determine which view to load
            if route_path == "/" or route_path == "/landing":
                view_content = landing.render_landing_view(state)
            elif route_path == "/dashboard":
                view_content = dashboard.render_dashboard_view(state)
            elif route_path == "/osint":
                view_content = osint.render_osint_view(state)
            elif route_path == "/humint":
                view_content = humint.render_humint_view(state)
            elif route_path == "/sigint":
                view_content = sigint.render_sigint_view(state)
            elif route_path == "/synth":
                view_content = synth.render_synth_view(state)
            elif route_path == "/geoint":
                view_content = geoint.render_geoint_view(state)
            elif route_path == "/anvil":
                view_content = anvil.render_anvil_view(state)
            else:
                # 404 - redirect to landing
                logger.warning(f"Unknown route: {route_path}, redirecting to /")
                page.go("/")
                return
            
            # Set the view content
            _shell.set_view_content(view_content)
        except ImportError as e:
            logger.error(f"Failed to import view: {e}")
            # Show error message
            _shell.set_view_content(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            style.mono_text(f"Error loading view: {e}", size=14, color=style.COLORS["error"]),
                            style.forge_button("Go to Landing", on_click=lambda _: page.go("/")),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                )
            )
        except Exception as e:
            logger.error(f"Route handler error: {e}", exc_info=True)
            # Fallback: try to load landing view
            try:
                from forge.frontend.views import landing
                view_content = landing.render_landing_view(state)
                _shell.set_view_content(view_content)
            except Exception as fallback_error:
                logger.error(f"Fallback view load also failed: {fallback_error}")
    
    # Set the route handler on the page - this is the SINGLE handler for all routes
    page.on_route_change = route_handler


def launch_ui(forge_state: ForgeState | None = None) -> int:
    """Launch the Forge UI in native desktop mode.
    
    Args:
        forge_state: Optional pre-initialized ForgeState. If None, one will be created.
        
    Returns:
        Exit code (0 for success)
    """
    # Store forge state globally if provided (will be picked up by main())
    if forge_state:
        # We'll need to pass this through somehow
        # For now, we'll rely on the global state init in main()
        pass
    
    try:
        # Launch Flet app
        # Note: window title is set in main() via page.title
        ft.app(
            target=main,
            view=ft.AppView.FLET_APP,
        )
        logger.info("Forge UI closed")
        return 0
    except Exception as e:
        logger.error(f"Failed to launch UI: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Direct launch for development
    import sys
    sys.exit(launch_ui())
