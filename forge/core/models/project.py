"""
Project Configuration for Forge 3.0.

Defines the ProjectManifest (configuration contract) and ProjectManager
for project lifecycle management.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Project Manifest
# ============================================================================


class ProjectManifest(BaseModel):
    """Canonical declaration of project configuration.
    
    Source of truth: project.json file in project directory.
    Defines entity schemas, LLM settings, and project metadata.
    
    Attributes:
        name: Project name
        description: Project description
        author: Project author
        version: Project version string
        schema_version: Database schema version for migrations
        entity_schemas: Dynamic field definitions per entity type
        relationship_schemas: Dynamic field definitions per relationship type
        llm_provider: LLM provider name
        llm_base_url: Optional API base URL
        llm_default_model: Default model ID
        template: Prefab template name
    """
    
    # Identity
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")
    author: str = Field(default="", description="Project author")
    version: str = Field(default="0.1.0", description="Project version")
    
    # Schema versioning
    schema_version: int = Field(default=1, description="Database schema version")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    last_modified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    
    # Dynamic schema definitions
    entity_schemas: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "actor": {},
            "polity": {},
            "location": {},
            "region": {},
            "resource": {},
            "event": {},
            "abstract": {},
        },
        description="Per-entity-type field schemas"
    )
    relationship_schemas: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-relationship-type field schemas"
    )
    
    # LLM configuration
    llm_provider: str = Field(
        default="openrouter",
        description="LLM provider (openrouter, cherry, lm_studio)"
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for LLM provider API"
    )
    llm_default_model: str = Field(
        default="",
        description="Default LLM model ID"
    )
    llm_fallback_model: Optional[str] = Field(
        default=None,
        description="Fallback model if primary unavailable"
    )
    
    # Embedding configuration
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Embedding vector dimension"
    )
    
    # Template / Prefab
    template: Optional[str] = Field(
        default=None,
        description="Prefab template name (e.g., 'default', 'espionage')"
    )
    
    # Custom settings
    custom_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Scenario-specific settings"
    )
    
    @classmethod
    def _normalize_schemas(cls, schemas: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Normalize schema field definitions.
        
        Supports both simple string types ("float") and rich definitions
        ({"type": "float", "required": True, "default": 0}).
        """
        normalized: dict[str, dict[str, Any]] = {}
        for type_name, fields in (schemas or {}).items():
            if not isinstance(fields, dict):
                continue
            
            norm_fields: dict[str, Any] = {}
            for field_name, field_def in fields.items():
                if isinstance(field_def, str):
                    norm_fields[field_name] = {"type": field_def}
                elif isinstance(field_def, dict):
                    norm_fields[field_name] = field_def
                else:
                    norm_fields[field_name] = {"type": str(field_def)}
            normalized[type_name] = norm_fields
        
        return normalized
    
    @field_validator("entity_schemas", mode="before")
    @classmethod
    def normalize_entity_schemas(cls, value):
        if isinstance(value, dict):
            return cls._normalize_schemas(value)
        return value
    
    @field_validator("relationship_schemas", mode="before")
    @classmethod
    def normalize_relationship_schemas(cls, value):
        if isinstance(value, dict):
            return cls._normalize_schemas(value)
        return value
    
    model_config = ConfigDict(frozen=False)
    
    def to_json(self) -> str:
        """Serialize manifest to JSON string."""
        return self.model_dump_json(indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ProjectManifest":
        """Deserialize manifest from JSON string."""
        return cls.model_validate_json(json_str)
    
    def get_entity_schema(self, entity_type: str) -> dict[str, Any]:
        """Get the field schema for a specific entity type."""
        return self.entity_schemas.get(entity_type.lower(), {})
    
    def get_relationship_schema(self, relationship_type: str) -> dict[str, Any]:
        """Get the field schema for a specific relationship type."""
        return self.relationship_schemas.get(relationship_type.lower(), {})


# ============================================================================
# Project Manager
# ============================================================================


class ProjectManager:
    """Manages project lifecycle: creation, loading, saving.
    
    Each project lives in its own directory with:
    - project.json: Configuration manifest
    - world.db: SQLite database with entities, relationships, embeddings
    - staging/: Extracted data awaiting merge
    """
    
    MANIFEST_FILE = "project.json"
    DATABASE_FILE = "world.db"
    STAGING_DIR = "staging"
    LOGS_DIR = "logs"
    
    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)
        self._manifest: Optional[ProjectManifest] = None

    def list_projects(self) -> list[str]:
        """List project directories in the configured projects root.
        
        Returns directories that contain a manifest file.
        """
        base = self.project_path
        if not base.exists() or base.is_file():
            return []
        return [
            p.name
            for p in base.iterdir()
            if p.is_dir() and (p / self.MANIFEST_FILE).exists()
        ]
    
    @property
    def manifest_path(self) -> Path:
        return self.project_path / self.MANIFEST_FILE
    
    @property
    def database_path(self) -> Path:
        return self.project_path / self.DATABASE_FILE
    
    @property
    def staging_path(self) -> Path:
        return self.project_path / self.STAGING_DIR
    
    @property
    def logs_path(self) -> Path:
        return self.project_path / self.LOGS_DIR
    
    @property
    def manifest(self) -> Optional[ProjectManifest]:
        return self._manifest
    
    def create_project(self, manifest: ProjectManifest) -> None:
        """Initialize a new project directory structure."""
        if self.project_path.exists():
            raise FileExistsError(f"Project already exists: {self.project_path}")
        
        # Create directories
        self.project_path.mkdir(parents=True)
        self.staging_path.mkdir()
        self.logs_path.mkdir()
        
        # Set timestamps
        manifest.created_at = datetime.now(UTC)
        manifest.last_modified_at = datetime.now(UTC)
        
        # Write manifest
        self.manifest_path.write_text(manifest.to_json(), encoding="utf-8")
        self._manifest = manifest
        
        # Configure ID counters
        try:
            from forge.core.models.entity import set_id_counters_path
            set_id_counters_path(self.project_path / ".id_counters.json")
        except Exception:
            pass
        
        # Initialize database
        self._init_database()
    
    def load_project(self) -> ProjectManifest:
        """Load an existing project."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        
        manifest_json = self.manifest_path.read_text(encoding="utf-8")
        manifest = ProjectManifest.from_json(manifest_json)
        self._manifest = manifest
        
        # Configure ID counters
        try:
            from forge.core.models.entity import set_id_counters_path
            set_id_counters_path(self.project_path / ".id_counters.json")
        except Exception:
            pass
        
        return manifest
    
    def save_manifest(self) -> None:
        """Save the current manifest to disk."""
        if self._manifest is None:
            raise ValueError("No manifest loaded")
        
        self._manifest.last_modified_at = datetime.now(UTC)
        self.manifest_path.write_text(self._manifest.to_json(), encoding="utf-8")
    
    def _init_database(self) -> None:
        """Initialize the world.db SQLite database with full schema."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                aliases_json TEXT DEFAULT '[]',
                tags_json TEXT DEFAULT '[]',
                attributes_json TEXT DEFAULT '{}',
                location_id TEXT,
                region_id TEXT,
                coordinates_json TEXT,
                layer TEXT DEFAULT 'terrestrial',
                source_documents_json TEXT DEFAULT '[]',
                embedding_row_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                label TEXT DEFAULT '',
                description TEXT DEFAULT '',
                strength REAL DEFAULT 1.0,
                visibility TEXT DEFAULT 'public',
                attributes_json TEXT DEFAULT '{}',
                source_documents_json TEXT DEFAULT '[]',
                embedding_row_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
        """)
        
        # Events log table (for Sentinel history/undo)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events_log (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source_id TEXT,
                target_id TEXT,
                description TEXT DEFAULT '',
                data_json TEXT DEFAULT '{}',
                is_rolled_back INTEGER DEFAULT 0
            )
        """)
        
        # Schema metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        cursor.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
            ("schema_version", str(self._manifest.schema_version if self._manifest else 1))
        )
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events_log(timestamp)")
        
        conn.commit()
        conn.close()
    
    def get_database_connection(self) -> sqlite3.Connection:
        """Get a connection to the world database."""
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")
        return sqlite3.connect(self.database_path)


# ============================================================================
# Helper Functions
# ============================================================================


def create_project(
    path: str | Path,
    name: str,
    description: str = "",
    author: str = "",
    template: str | None = None,
) -> ProjectManager:
    """Create a new project with default settings."""
    manifest = ProjectManifest(
        name=name,
        description=description,
        author=author,
        template=template,
    )
    
    manager = ProjectManager(path)
    manager.create_project(manifest)
    return manager


def load_project(path: str | Path) -> ProjectManager:
    """Load an existing project."""
    manager = ProjectManager(path)
    manager.load_project()
    return manager
