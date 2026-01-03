"""PyScrAI|Forge

This is now PyScrAI|Forge with 3-state UI architecture:
- LANDING: Initial state for project selection
- DASHBOARD: Project overview and quick actions  
- COMPONENT_EDITOR: Full entity/relationship editing interface

Usage:
    python -m pyscrai_forge.src.forge [packet_file.json]
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class AppState(Enum):
    """Application states for UI navigation."""
    LANDING = "landing"
    DASHBOARD = "dashboard"
    COMPONENT_EDITOR = "component_editor"


# Main Function (needed for module execution pattern)
def main(packet_path: Path | None = None, project_path: Path | None = None) -> None:
    """Main entry point for forge.
    
    This function now delegates to the refactored app structure.
    The old ReviewerApp class is kept for backward compatibility.
    """
    # Use the new refactored app structure
    from pyscrai_forge.src.app.main_app import ReviewerApp as NewReviewerApp
    app = NewReviewerApp(packet_path=packet_path, project_path=project_path)
    app.root.mainloop()