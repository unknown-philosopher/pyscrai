"""
Forge 3.0 Main Application.

Entry point for the Forge narrative intelligence system.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forge.app.config import ForgeConfig
    from forge.app.state import ForgeState


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="forge",
        description="PyScrAI | Forge 3.0 - Narrative Intelligence System",
    )
    
    parser.add_argument(
        "--project", "-p",
        help="Project name to open on startup",
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file",
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Run in headless mode without UI",
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Forge 3.0.0",
    )
    
    return parser.parse_args()


def setup_environment(args: argparse.Namespace) -> "ForgeConfig":
    """Set up the application environment.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Loaded configuration
    """
    from forge.app.config import ForgeConfig, set_config
    from forge.utils.logging import setup_logging
    
    # Load configuration
    config_path = Path(args.config) if args.config else None
    config = ForgeConfig.load(config_path)
    
    # Override log level from command line
    if args.log_level:
        config.log_level = args.log_level
    
    # Set up logging
    setup_logging(
        level=config.log_level,
        log_dir=config.data_dir / "logs",
        console_output=True,
        file_output=True,
    )
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Set as global config
    set_config(config)
    
    return config


def initialize_application(config: "ForgeConfig") -> "ForgeState":
    """Initialize the application state.
    
    Args:
        config: Application configuration
        
    Returns:
        Initialized application state
    """
    from forge.app.state import init_state
    from forge.utils.logging import get_logger
    
    logger = get_logger("app")
    logger.info("Initializing Forge 3.0...")
    
    # Initialize global state
    state = init_state(config)
    
    return state


def run_ui(state: "ForgeState") -> int:
    """Launch the Forge UI.
    
    Args:
        state: Application state
        
    Returns:
        Exit code
    """
    from forge.utils.logging import get_logger
    
    logger = get_logger("app")
    logger.info("Starting Forge UI (Flet)...")
    
    try:
        # Launch Flet frontend
        from forge.frontend.main import launch_ui
        return launch_ui(state)
        
    except ImportError as e:
        logger.warning(f"Flet not available: {e}")
        logger.warning("Falling back to demo mode. Install with: pip install flet")
        _run_demo(state)
        return 0
        
    except Exception as e:
        logger.error(f"UI error: {e}", exc_info=True)
        return 1


def run_headless(state: "ForgeState", project_name: str | None) -> int:
    """Run Forge in headless mode.
    
    Args:
        state: Application state
        project_name: Optional project to load
        
    Returns:
        Exit code
    """
    from forge.utils.logging import get_logger
    
    logger = get_logger("app")
    logger.info("Running in headless mode")
    
    try:
        if project_name:
            state.load_project(project_name)
            stats = state.get_stats()
            logger.info(f"Project stats: {stats}")
        else:
            logger.info("No project specified. Use --project to specify one.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Headless mode error: {e}", exc_info=True)
        return 1


def _run_demo(state: "ForgeState") -> None:
    """Run a demo to verify systems work.
    
    Args:
        state: Application state
    """
    from forge.utils.logging import get_logger
    
    logger = get_logger("app.demo")
    
    logger.info("=" * 50)
    logger.info("Forge 3.0 Demo")
    logger.info("=" * 50)
    
    # Show config
    logger.info(f"Data directory: {state.config.data_dir}")
    logger.info(f"Projects directory: {state.config.projects_dir}")
    logger.info(f"LLM provider: {state.config.llm.provider}")
    logger.info(f"LLM model: {state.config.llm.model}")
    
    # Try to list projects
    from forge.core.models.project import ProjectManager
    
    pm = ProjectManager(state.config.projects_dir)
    projects = pm.list_projects()
    
    logger.info(f"Available projects: {projects}")
    
    if projects:
        # Load first project
        state.load_project(projects[0])
        stats = state.get_stats()
        logger.info(f"Project stats: {stats}")
        state.close_project()
    
    logger.info("=" * 50)
    logger.info("Demo complete")
    logger.info("=" * 50)


def main() -> int:
    """Main entry point for Forge.
    
    Returns:
        Exit code
    """
    args = parse_args()
    
    try:
        # Setup
        config = setup_environment(args)
        state = initialize_application(config)
        
        # Load project if specified
        if args.project:
            state.load_project(args.project)
        
        # Run appropriate mode
        if args.no_ui:
            return run_headless(state, args.project)
        else:
            return run_ui(state)
        
    except KeyboardInterrupt:
        print("\nForge terminated by user.")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
