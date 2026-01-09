"""
Forge Configuration.

Central configuration management for Forge 3.0.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


# ============================================================================
# Default Paths
# ============================================================================


def get_default_data_dir() -> Path:
    """Get the default data directory for Forge."""
    # Check for environment override
    if env_path := os.environ.get("FORGE_DATA_DIR"):
        return Path(env_path)
    
    # Use the standard location relative to package
    return Path(__file__).parent.parent.parent / "data"


def get_default_projects_dir() -> Path:
    """Get the default projects directory."""
    return get_default_data_dir() / "projects"


def get_default_templates_dir() -> Path:
    """Get the default templates directory."""
    return Path(__file__).parent.parent / "prefabs" / "templates"


# ============================================================================
# Configuration Classes
# ============================================================================


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    
    provider: Literal["openrouter", "cherry", "lm_studio", "lm_proxy"] = "openrouter"
    model: str = "openai/gpt-4.1-mini"
    api_key: str | None = None  # Falls back to environment variable
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        return cls(
            provider=data.get("provider", "openrouter"),
            model=data.get("model", "openai/gpt-4.1-mini"),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            # Don't serialize API key for security
        }


@dataclass
class ExtractionConfig:
    """Configuration for the extraction phase."""
    
    chunk_size: int = 2500  # Tokens per chunk
    chunk_overlap: int = 500  # Overlap between chunks
    similarity_threshold: float = 0.85  # For near-duplicate detection
    auto_merge_threshold: float = 0.95  # Threshold for automatic merging
    max_entities_per_chunk: int = 15  # Max entities to extract per chunk
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtractionConfig":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "similarity_threshold": self.similarity_threshold,
            "auto_merge_threshold": self.auto_merge_threshold,
            "max_entities_per_chunk": self.max_entities_per_chunk,
        }


@dataclass
class UIConfig:
    """Configuration for the UI."""
    
    theme: Literal["dark", "light"] = "dark"
    window_width: int = 1400
    window_height: int = 900
    font_family: str = "Segoe UI"
    font_size: int = 10
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UIConfig":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "font_family": self.font_family,
            "font_size": self.font_size,
        }


@dataclass
class ForgeConfig:
    """Main configuration for Forge.
    
    Aggregates all sub-configurations and provides load/save functionality.
    """
    
    # Paths
    data_dir: Path = field(default_factory=get_default_data_dir)
    projects_dir: Path = field(default_factory=get_default_projects_dir)
    templates_dir: Path = field(default_factory=get_default_templates_dir)
    
    # Sub-configs
    llm: LLMConfig = field(default_factory=LLMConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    def __post_init__(self):
        # Ensure paths are Path objects
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        if isinstance(self.projects_dir, str):
            self.projects_dir = Path(self.projects_dir)
        if isinstance(self.templates_dir, str):
            self.templates_dir = Path(self.templates_dir)
    
    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "ForgeConfig":
        """Load configuration from a JSON file.
        
        Args:
            config_path: Path to config file. If None, uses default location.
            
        Returns:
            ForgeConfig instance
        """
        if config_path is None:
            config_path = get_default_data_dir() / "user" / "default" / "forge_config.json"
        
        config_path = Path(config_path)
        
        if not config_path.exists():
            return cls()
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForgeConfig":
        """Create config from dictionary."""
        return cls(
            data_dir=Path(data.get("data_dir", get_default_data_dir())),
            projects_dir=Path(data.get("projects_dir", get_default_projects_dir())),
            templates_dir=Path(data.get("templates_dir", get_default_templates_dir())),
            llm=LLMConfig.from_dict(data.get("llm", {})),
            extraction=ExtractionConfig.from_dict(data.get("extraction", {})),
            ui=UIConfig.from_dict(data.get("ui", {})),
            log_level=data.get("log_level", "INFO"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "data_dir": str(self.data_dir),
            "projects_dir": str(self.projects_dir),
            "templates_dir": str(self.templates_dir),
            "llm": self.llm.to_dict(),
            "extraction": self.extraction.to_dict(),
            "ui": self.ui.to_dict(),
            "log_level": self.log_level,
        }
    
    def save(self, config_path: str | Path | None = None) -> Path:
        """Save configuration to a JSON file.
        
        Args:
            config_path: Path to save to. If None, uses default location.
            
        Returns:
            Path to saved file
        """
        if config_path is None:
            config_path = self.data_dir / "user" / "default" / "forge_config.json"
        
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return config_path
    
    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        if self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Global Config Instance
# ============================================================================


_global_config: ForgeConfig | None = None


def get_config() -> ForgeConfig:
    """Get the global configuration instance.
    
    Returns:
        ForgeConfig singleton
    """
    global _global_config
    if _global_config is None:
        _global_config = ForgeConfig.load()
    return _global_config


def set_config(config: ForgeConfig) -> None:
    """Set the global configuration instance.
    
    Args:
        config: Configuration to set
    """
    global _global_config
    _global_config = config


def reload_config(config_path: str | Path | None = None) -> ForgeConfig:
    """Reload configuration from disk.
    
    Args:
        config_path: Optional path to load from
        
    Returns:
        Newly loaded configuration
    """
    global _global_config
    _global_config = ForgeConfig.load(config_path)
    return _global_config
