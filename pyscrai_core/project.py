"""Project management and lifecycle for PyScrAI.

This module defines the ProjectManifest, ProjectController, and schema migration system.
Updated to support Project-Defined Entity Schemas.
"""

import json
import os
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Project Manifest (Configuration Contract)
# ============================================================================


class ProjectManifest(BaseModel):
    """Canonical declaration of project configuration.

    Source of truth: project.json file in bundle root.
    
    Includes `entity_schemas` to define the "truth" for this specific simulation world.
    """

    # Identity
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")
    author: str = Field(default="", description="Project author")
    version: str = Field(default="0.1.0", description="Project version")

    # Schema
    schema_version: int = Field(default=1, description="Database schema version")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    last_modified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last modification timestamp"
    )

    # --- DYNAMIC SCHEMA DEFINITION ---
    # This dictionary defines valid fields for StateComponent.resources_json
    # Format: { "polity": { "treasury": "float", "stability": "float" }, "actor": {...} }
    entity_schemas: dict[str, dict[str, str]] = Field(
        default_factory=lambda: {
            "polity": {},
            "actor": {},
            "location": {},
            "abstract": {}
        },
        description="Project-specific schemas for entity resources (stats)"
    )

    # Systems configuration
    enabled_systems: list[str] = Field(
        default_factory=lambda: ["events", "memory", "relationships"],
        description="Enabled simulation systems",
    )

    # LLM configuration
    llm_provider: str = Field(
        default="openrouter", description="LLM provider (openrouter, lmstudio, ollama)"
    )
    llm_default_model: str = Field(
        default="", description="Default LLM model ID for AI agents"
    )
    llm_fallback_model: Optional[str] = Field(
        default=None, description="Fallback model if primary unavailable"
    )

    # Memory backend
    memory_backend: str = Field(
        default="chromadb_local", description="Memory backend (chromadb_local, chromadb_remote)"
    )
    memory_collection_id: str = Field(
        default="", description="ChromaDB collection identifier"
    )

    # Snapshots (for O(1) load times)
    snapshot_interval: int = Field(
        default=100, ge=1, description="Create snapshot every N turns"
    )

    # Simulation settings
    tick_duration_seconds: float = Field(
        default=1.0, ge=0.0, description="Real-time seconds per simulation tick"
    )
    max_concurrent_agents: int = Field(
        default=10, ge=1, description="Maximum agents processing simultaneously"
    )

    # Mod dependencies
    dependencies: dict[str, str] = Field(
        default_factory=dict, description="Mod dependencies: {mod_name: version}"
    )

    # Custom settings (escape hatch for scenario-specific config)
    custom_settings: str = Field(
        default="{}",
        description="JSON string for scenario-specific settings",
    )

    class Config:
        frozen = False

    @property
    def custom(self) -> dict[str, Any]:
        """Get custom settings as dictionary."""
        try:
            return json.loads(self.custom_settings) if self.custom_settings else {}
        except json.JSONDecodeError:
            return {}

    def to_json(self) -> str:
        """Serialize manifest to JSON string."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ProjectManifest":
        """Deserialize manifest from JSON string."""
        return cls.model_validate_json(json_str)


# ============================================================================
# Schema Migration Tracking
# ============================================================================


class SchemaMigration(BaseModel):
    """Audit trail for schema changes."""
    id: str = Field(description="Migration identifier")
    from_version: int = Field(description="Source schema version")
    to_version: int = Field(description="Target schema version")
    applied_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When migration was applied"
    )
    migration_script: str = Field(
        default="", description="SQL or Python migration script name"
    )
    success: bool = Field(default=True, description="Whether migration succeeded")
    error_message: Optional[str] = Field(
        default=None, description="Error message if migration failed"
    )

    class Config:
        frozen = True


# ============================================================================
# Project Controller (Lifecycle Management)
# ============================================================================


class ProjectController:
    """Manages project lifecycle: creation, loading, export, migration."""

    MANIFEST_FILE = "project.json"
    DATABASE_FILE = "world.db"
    CHROMA_DIR = "chroma_store"
    ASSETS_DIR = "assets"
    LOGS_DIR = "logs"

    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)
        self._manifest: Optional[ProjectManifest] = None

    @property
    def manifest_path(self) -> Path:
        return self.project_path / self.MANIFEST_FILE

    @property
    def database_path(self) -> Path:
        return self.project_path / self.DATABASE_FILE

    @property
    def chroma_path(self) -> Path:
        return self.project_path / self.CHROMA_DIR

    @property
    def assets_path(self) -> Path:
        return self.project_path / self.ASSETS_DIR

    @property
    def logs_path(self) -> Path:
        return self.project_path / self.LOGS_DIR

    @property
    def manifest(self) -> Optional[ProjectManifest]:
        return self._manifest

    def create_project(self, manifest: ProjectManifest) -> None:
        """Initialize new project bundle structure."""
        if self.project_path.exists():
            raise FileExistsError(f"Project already exists: {self.project_path}")

        self.project_path.mkdir(parents=True)
        self.chroma_path.mkdir()
        self.assets_path.mkdir()
        (self.assets_path / "maps").mkdir()
        (self.assets_path / "images").mkdir()
        self.logs_path.mkdir()

        manifest.created_at = datetime.now(UTC)
        manifest.last_modified_at = datetime.now(UTC)
        self.manifest_path.write_text(manifest.to_json(), encoding="utf-8")
        self._manifest = manifest

        self._init_database(manifest.schema_version)

    def load_project(self) -> ProjectManifest:
        """Load and validate existing project."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")

        manifest_json = self.manifest_path.read_text(encoding="utf-8")
        manifest = ProjectManifest.from_json(manifest_json)

        db_version = self._get_database_schema_version()
        if db_version != manifest.schema_version:
            raise ValueError(
                f"Schema version mismatch: manifest={manifest.schema_version}, "
                f"database={db_version}. Run migrate_schema() first."
            )

        self._manifest = manifest
        return manifest

    def save_manifest(self) -> None:
        """Save current manifest to project.json."""
        if self._manifest is None:
            raise ValueError("No manifest loaded. Call load_project() or create_project() first.")

        self._manifest.last_modified_at = datetime.now(UTC)
        self.manifest_path.write_text(self._manifest.to_json(), encoding="utf-8")

    def export_bundle(self, output_path: str | Path) -> Path:
        """Package project into .pyscrai zip bundle."""
        if self._manifest is None:
            raise ValueError("No project loaded. Call load_project() first.")

        output_path = Path(output_path)
        bundle_path = output_path.with_suffix(".pyscrai")

        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.project_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.project_path)
                    zf.write(file_path, arcname)

        return bundle_path

    @classmethod
    def import_bundle(cls, bundle_path: str | Path, extract_to: str | Path) -> "ProjectController":
        """Extract .pyscrai bundle to directory."""
        bundle_path = Path(bundle_path)
        extract_to = Path(extract_to)

        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")

        if extract_to.exists():
            raise FileExistsError(f"Destination already exists: {extract_to}")

        with zipfile.ZipFile(bundle_path, "r") as zf:
            zf.extractall(extract_to)

        controller = cls(extract_to)
        controller.load_project()
        return controller

    def migrate_schema(self, target_version: int) -> list[SchemaMigration]:
        """Apply forward-only schema migrations."""
        if self._manifest is None:
            raise ValueError("No project loaded. Call load_project() first.")

        current_version = self._manifest.schema_version
        if target_version < current_version:
            raise ValueError(
                f"Downgrades not supported: current={current_version}, target={target_version}"
            )

        migrations: list[SchemaMigration] = []

        for version in range(current_version + 1, target_version + 1):
            migration = self._apply_migration(current_version, version)
            migrations.append(migration)
            current_version = version

        self._manifest.schema_version = target_version
        self.save_manifest()

        return migrations

    def _init_database(self, schema_version: int) -> None:
        """Initialize empty database with schema version table."""
        import sqlite3

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                applied_at TEXT NOT NULL,
                migration_script TEXT
            )
        """)

        cursor.execute(
            "INSERT INTO schema_versions (version, applied_at) VALUES (?, ?)",
            (schema_version, datetime.now(UTC).isoformat()),
        )

        conn.commit()
        conn.close()

    def _get_database_schema_version(self) -> int:
        """Get current schema version from database."""
        import sqlite3

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT MAX(version) FROM schema_versions")
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 1
        except sqlite3.OperationalError:
            return 1
        finally:
            conn.close()

    def _apply_migration(self, from_version: int, to_version: int) -> SchemaMigration:
        """Apply a single schema migration."""
        import sqlite3
        import uuid

        migration = SchemaMigration(
            id=str(uuid.uuid4()),
            from_version=from_version,
            to_version=to_version,
            migration_script=f"migration_{from_version}_to_{to_version}.py",
        )

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO schema_versions (version, applied_at, migration_script)
                VALUES (?, ?, ?)
                """,
                (to_version, migration.applied_at.isoformat(), migration.migration_script),
            )
            conn.commit()
        except Exception as e:
            migration = SchemaMigration(
                id=migration.id,
                from_version=from_version,
                to_version=to_version,
                success=False,
                error_message=str(e),
            )
        finally:
            conn.close()

        return migration

    def delete_project(self) -> None:
        """Delete entire project directory."""
        if self.project_path.exists():
            shutil.rmtree(self.project_path)
        self._manifest = None