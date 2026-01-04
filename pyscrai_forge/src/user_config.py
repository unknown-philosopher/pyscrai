"""User configuration and preferences management for PyScrAI|Forge."""

from pathlib import Path
from datetime import datetime, UTC
from typing import Optional
from pydantic import BaseModel, Field
import json
import os
import logging

from pyscrai_forge.src.logging_config import get_logger

class RecentProject(BaseModel):
    """Recent project entry."""
    path: str
    name: str
    last_opened: datetime


class UserPreferences(BaseModel):
    """User preferences."""
    auto_load_last_project: bool = False
    theme: str = "default"


class WindowGeometry(BaseModel):
    """Window geometry settings."""
    main_window: str = "1400x900"
    last_state: str = "LANDING"


class UserConfig(BaseModel):
    """User configuration model."""
    version: str = "1.0"
    recent_projects: list[RecentProject] = Field(default_factory=list)
    max_recent_projects: int = 10
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    window_geometry: WindowGeometry = Field(default_factory=WindowGeometry)

    @classmethod
    def get_config_path(cls) -> Path:
        """Get user config file path (cross-platform)."""
        # Windows: %APPDATA%/pyscrai/user_config.json
        # macOS/Linux: ~/.config/pyscrai/user_config.json
        if os.name == 'nt':
            base = Path(os.environ.get('APPDATA', str(Path.home())))
        else:
            base = Path.home() / '.config'
        
        config_dir = base / 'pyscrai'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'user_config.json'

    @classmethod
    def load(cls) -> 'UserConfig':
        """Load user config from disk."""
        logger = get_logger("UserConfig")
        path = cls.get_config_path()
        if path.exists():
            try:
                config = cls.model_validate_json(path.read_text(encoding='utf-8'))
                logger.info(f"User config loaded from: {path}")
                return config
            except Exception as e:
                logger.error(f"Failed to load user config: {e}. Using defaults.")
        else:
            logger.info("No user config found, using defaults.")
        return cls()

    def save(self) -> None:
        """Save user config to disk."""
        logger = get_logger("UserConfig")
        try:
            path = self.get_config_path()
            path.write_text(self.model_dump_json(indent=2), encoding='utf-8')
            logger.info(f"User config saved to: {path}")
        except Exception as e:
            logger.error(f"Failed to save user config: {e}")

    def add_recent_project(self, project_path: Path, project_name: str) -> None:
        """Add project to recent list."""
        get_logger("UserConfig").info(f"Adding recent project: {project_name} ({project_path})")
        # Remove if already exists
        self.recent_projects = [
            p for p in self.recent_projects if p.path != str(project_path)
        ]
        # Add to front
        self.recent_projects.insert(0, RecentProject(
            path=str(project_path),
            name=project_name,
            last_opened=datetime.now(UTC)
        ))
        # Trim to max
        self.recent_projects = self.recent_projects[:self.max_recent_projects]
        # Save via ConfigManager if available, otherwise direct save
        self._save_via_manager_or_direct()
    
    def clear_recent_projects(self) -> None:
        """Clear recent projects list."""
        self.recent_projects = []
        self._save_via_manager_or_direct()
    
    def _save_via_manager_or_direct(self) -> None:
        """Save via ConfigManager if available, otherwise direct save."""
        try:
            from pyscrai_forge.src.config_manager import ConfigManager
            config_mgr = ConfigManager.get_instance()
            # Update ConfigManager's reference to this instance
            config_mgr._config = self
            config_mgr.save_config()
        except Exception:
            # Fallback to direct save if ConfigManager not available
            self.save()
