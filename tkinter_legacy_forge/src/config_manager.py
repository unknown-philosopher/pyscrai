"""Centralized configuration management for PyScrAI|Forge.

Provides a singleton pattern for accessing and managing user configuration.
This ensures consistent configuration access across the application and
prevents multiple instances of UserConfig from getting out of sync.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pyscrai_forge.src.user_config import UserConfig


class ConfigManager:
    """Singleton manager for user configuration.
    
    Provides centralized access to UserConfig, ensuring only one instance
    exists and all components use the same configuration state.
    
    Example:
        >>> config = ConfigManager.get_instance()
        >>> user_config = config.get_config()
        >>> user_config.preferences.theme = "dark"
        >>> config.save_config()
    """
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional['UserConfig'] = None
    
    def __init__(self):
        """Initialize the config manager (private - use get_instance())."""
        if ConfigManager._instance is not None:
            raise RuntimeError("ConfigManager is a singleton. Use get_instance() instead.")
        self._config = None
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """Get the singleton instance of ConfigManager.
        
        Returns:
            The ConfigManager singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_config(self) -> 'UserConfig':
        """Get the user configuration, loading it if necessary.
        
        Returns:
            The UserConfig instance
        """
        if self._config is None:
            from pyscrai_forge.src.user_config import UserConfig
            self._config = UserConfig.load()
        return self._config
    
    def save_config(self) -> None:
        """Save the current user configuration to disk."""
        if self._config:
            try:
                self._config.save()
            except Exception as e:
                print(f"Failed to save user config: {e}")
    
    def reload_config(self) -> 'UserConfig':
        """Reload configuration from disk, discarding any in-memory changes.
        
        Returns:
            The reloaded UserConfig instance
        """
        from pyscrai_forge.src.user_config import UserConfig
        self._config = UserConfig.load()
        return self._config
    
    def reset_instance(self) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls = ConfigManager
        cls._instance = None
        cls._config = None

