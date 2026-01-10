"""
Forge Application State.

Manages global runtime state including the active project,
database connections, and LLM providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.config import ForgeConfig
    from forge.core.models.project import ProjectManifest
    from forge.systems.llm.base import LLMProvider
    from forge.systems.memory.vector_memory import VectorMemory
    from forge.systems.storage.database import DatabaseManager
    from forge.systems.storage.file_io import FileManager


logger = get_logger("app.state")


# ============================================================================
# Application State
# ============================================================================


@dataclass
class ForgeState:
    """Runtime state for the Forge application.
    
    This is a mutable container holding all active resources
    for the current session. It provides a single point of access
    for the UI and phases to interact with core systems.
    
    Usage:
        state = ForgeState.create(config)
        state.load_project("my_project")
        
        # Access systems
        state.db.save_entity(entity)
        response = await state.llm.generate(messages)
    """
    
    # Configuration
    config: "ForgeConfig"
    
    # Active project
    project: "ProjectManifest | None" = None
    
    # System instances (initialized lazily)
    _db: "DatabaseManager | None" = field(default=None, repr=False)
    _file_manager: "FileManager | None" = field(default=None, repr=False)
    _vector_memory: "VectorMemory | None" = field(default=None, repr=False)
    _llm_provider: "LLMProvider | None" = field(default=None, repr=False)
    
    # Runtime metadata
    session_id: str = ""
    dirty: bool = False  # Indicates unsaved changes
    
    @classmethod
    def create(cls, config: "ForgeConfig") -> "ForgeState":
        """Create a new application state.
        
        Args:
            config: Forge configuration
            
        Returns:
            Initialized state instance
        """
        from forge.utils.ids import generate_session_id
        
        return cls(
            config=config,
            session_id=generate_session_id(),
        )
    
    # ========== Project Management ==========
    
    def load_project(self, project_name: str) -> "ProjectManifest":
        """Load a project and initialize its systems.
        
        Args:
            project_name: Name of the project to load
            
        Returns:
            Loaded project manifest
            
        Raises:
            FileNotFoundError: If project doesn't exist
        """
        from forge.core.models.project import ProjectManager
        
        # ProjectManager needs the full path to the specific project
        project_path = self.config.projects_dir / project_name
        pm = ProjectManager(project_path)
        self.project = pm.load_project()
        
        # Reset system instances for new project
        self._db = None
        self._file_manager = None
        self._vector_memory = None
        self.dirty = False
        
        logger.info(f"Loaded project: {project_name}")
        return self.project
    
    def create_project(
        self,
        name: str,
        description: str = "",
        **kwargs: Any,
    ) -> "ProjectManifest":
        """Create a new project.
        
        Args:
            name: Project name
            description: Project description
            **kwargs: Additional project settings
            
        Returns:
            Created project manifest
        """
        from forge.core.models.project import ProjectManager, ProjectManifest
        
        # Create the project directory path
        project_path = self.config.projects_dir / name
        
        # Create manifest with provided info
        manifest = ProjectManifest(
            name=name,
            description=description,
            **kwargs,
        )
        
        pm = ProjectManager(project_path)
        pm.create_project(manifest)
        self.project = manifest
        
        # Reset system instances
        self._db = None
        self._file_manager = None
        self._vector_memory = None
        self.dirty = False
        
        logger.info(f"Created project: {name}")
        return self.project
    
    def save_project(self) -> None:
        """Save the current project manifest."""
        if self.project is None:
            raise RuntimeError("No project loaded")
        
        from forge.core.models.project import ProjectManager
        
        pm = ProjectManager(self.config.projects_dir)
        pm.save_project(self.project)
        self.dirty = False
        
        logger.info(f"Saved project: {self.project.name}")
    
    def close_project(self) -> None:
        """Close the current project and clean up resources."""
        if self._db is not None:
            self._db.close()
            self._db = None
        
        self._file_manager = None
        self._vector_memory = None
        
        old_name = self.project.name if self.project else "None"
        self.project = None
        self.dirty = False
        
        logger.info(f"Closed project: {old_name}")
    
    @property
    def has_project(self) -> bool:
        """Check if a project is loaded."""
        return self.project is not None
    
    @property
    def project_path(self) -> str:
        """Get the current project path."""
        if self.project is None:
            raise RuntimeError("No project loaded")
        return str(self.config.projects_dir / self.project.name)
    
    # ========== System Accessors ==========
    
    @property
    def db(self) -> "DatabaseManager":
        """Get the database manager for the current project.
        
        Lazily initializes the connection on first access.
        """
        if self.project is None:
            raise RuntimeError("No project loaded")
        
        if self._db is None:
            from forge.systems.storage.database import DatabaseManager
            
            db_path = self.config.projects_dir / self.project.name / "world.db"
            self._db = DatabaseManager(db_path)
            self._db.initialize()
            logger.debug(f"Initialized database: {db_path}")
        
        return self._db
    
    @property
    def files(self) -> "FileManager":
        """Get the file manager for the current project."""
        if self.project is None:
            raise RuntimeError("No project loaded")
        
        if self._file_manager is None:
            from forge.systems.storage.file_io import FileManager
            
            project_path = self.config.projects_dir / self.project.name
            self._file_manager = FileManager(project_path)
            self._file_manager.ensure_directories()
            logger.debug(f"Initialized file manager: {project_path}")
        
        return self._file_manager
    
    @property
    def memory(self) -> "VectorMemory":
        """Get the vector memory for the current project."""
        if self.project is None:
            raise RuntimeError("No project loaded")
        
        if self._vector_memory is None:
            from forge.systems.memory.vector_memory import VectorMemory
            
            db_path = self.config.projects_dir / self.project.name / "world.db"
            self._vector_memory = VectorMemory(db_path)
            logger.debug(f"Initialized vector memory: {db_path}")
        
        return self._vector_memory
    
    @property
    def llm(self) -> "LLMProvider":
        """Get the LLM provider (shared across projects)."""
        if self._llm_provider is None:
            from forge.systems.llm.provider_factory import ProviderFactory, ProviderType
            
            provider_type = ProviderType(self.config.llm.provider)
            
            self._llm_provider = ProviderFactory.create(
                provider_type,
                api_key=self.config.llm.api_key,
                base_url=self.config.llm.base_url,
            )
            logger.debug(f"Initialized LLM provider: {provider_type.value}")
        
        return self._llm_provider
    
    def set_llm_provider(self, provider: "LLMProvider") -> None:
        """Set a custom LLM provider.
        
        Args:
            provider: LLM provider instance
        """
        self._llm_provider = provider
        logger.debug(f"Set custom LLM provider: {type(provider).__name__}")
    
    # ========== State Operations ==========
    
    def mark_dirty(self) -> None:
        """Mark the project as having unsaved changes."""
        self.dirty = True
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the current state.
        
        Returns:
            Dict with project stats
        """
        stats = {
            "session_id": self.session_id,
            "has_project": self.has_project,
            "dirty": self.dirty,
        }
        
        if self.has_project:
            stats["project_name"] = self.project.name
            stats.update(self.db.get_stats())
        
        return stats


# ============================================================================
# Global State Instance
# ============================================================================


_global_state: ForgeState | None = None


def get_state() -> ForgeState:
    """Get the global application state.
    
    Returns:
        ForgeState singleton
        
    Raises:
        RuntimeError: If state hasn't been initialized
    """
    if _global_state is None:
        raise RuntimeError("Application state not initialized. Call init_state() first.")
    return _global_state


def init_state(config: "ForgeConfig | None" = None) -> ForgeState:
    """Initialize the global application state.
    
    Args:
        config: Configuration to use. If None, loads default.
        
    Returns:
        Initialized state instance
    """
    global _global_state
    
    if config is None:
        from forge.app.config import get_config
        config = get_config()
    
    _global_state = ForgeState.create(config)
    logger.info(f"Initialized Forge state (session: {_global_state.session_id})")
    
    return _global_state


def reset_state() -> None:
    """Reset the global state (for testing)."""
    global _global_state
    
    if _global_state is not None:
        if _global_state.has_project:
            _global_state.close_project()
    
    _global_state = None
