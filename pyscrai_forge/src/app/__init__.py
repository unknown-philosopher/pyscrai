"""PyScrAI|Forge Application Module

Refactored application structure with focused manager classes.
"""

from .main_app import ReviewerApp, main
from .state_manager import AppStateManager, AppState
from .menu_manager import MenuManager
from .project_manager import ProjectController
from .data_manager import DataManager

__all__ = [
    "ReviewerApp",
    "main",
    "AppStateManager",
    "AppState",
    "MenuManager",
    "ProjectController",
    "DataManager",
]

