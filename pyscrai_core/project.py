"""Project management and lifecycle for PyScrAI.

This module defines the ProjectManifest, ProjectController, and schema migration system.
Updated to support Project-Defined Entity Schemas.
"""

import json
import os
import shutil
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .models import (
    Actor,
    Entity,
    EntityType,
    Location,
    Polity,
    Relationship,
    RelationshipType,
    RelationshipVisibility,
)


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

    # Template assignment
    template: Optional[str] = Field(
        default=None, description="Template directory name (e.g., 'default', 'espionage', 'historical')"
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

        # Configure ID counters persistence for this project
        try:
            from .models import set_id_counters_path
            set_id_counters_path(self.project_path / ".id_counters.json")
        except Exception:
            pass

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
        # Configure ID counters persistence for this project
        try:
            from .models import set_id_counters_path
            set_id_counters_path(self.project_path / ".id_counters.json")
        except Exception:
            pass
        return manifest

    def get_all_entities(self) -> list[Entity]:
        """Load every entity from the world database."""
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT data_json FROM entities ORDER BY created_at")
        rows = cursor.fetchall()
        conn.close()

        entities: list[Entity] = []
        for row in rows:
            try:
                data = json.loads(row[0])
                entity_type_str = data.get("descriptor", {}).get("entity_type", "ABSTRACT")
                try:
                    entity_type = EntityType(entity_type_str)
                except ValueError:
                    entity_type = EntityType.ABSTRACT

                if entity_type == EntityType.ACTOR:
                    entities.append(Actor.model_validate(data))
                elif entity_type == EntityType.POLITY:
                    entities.append(Polity.model_validate(data))
                elif entity_type == EntityType.LOCATION:
                    entities.append(Location.model_validate(data))
                else:
                    entities.append(Entity.model_validate(data))
            except Exception:
                continue

        return entities

    def get_all_relationships(self) -> list[Relationship]:
        """Load every relationship from the world database."""
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT source_id, target_id, relationship_type, strength, description, data_json
            FROM relationships
            ORDER BY created_at
            """
        )
        rows = cursor.fetchall()
        conn.close()

        relationships: list[Relationship] = []
        for row in rows:
            try:
                source_id, target_id, rel_type_str, strength, description, data_json = row
                data = json.loads(data_json) if data_json else {}

                try:
                    rel_type = RelationshipType(rel_type_str)
                except ValueError:
                    rel_type = RelationshipType.CUSTOM

                visibility_str = data.get("visibility", "public").lower()
                try:
                    visibility = RelationshipVisibility(visibility_str)
                except ValueError:
                    visibility = RelationshipVisibility.PUBLIC

                metadata_raw = data.get("metadata", "{}")
                metadata_json = json.dumps(metadata_raw) if isinstance(metadata_raw, dict) else str(metadata_raw)

                relationships.append(
                    Relationship(
                        id=f"rel_{source_id[:8]}_{target_id[:8]}_{rel_type.value}",
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=rel_type,
                        visibility=visibility,
                        strength=strength,
                        description=description or "",
                        metadata=metadata_json,
                    )
                )
            except Exception:
                continue

        return relationships

    # ------------------------------------------------------------------
    # Persistence helpers (engine writes)
    # ------------------------------------------------------------------
    def _ensure_entity_tables(self) -> None:
        """Ensure entities/relationships tables exist (idempotent)."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL NOT NULL,
                description TEXT,
                data_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")

        conn.commit()
        conn.close()

    def update_entity(self, entity: Entity) -> None:
        """Insert or update an entity in the database."""
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")

        self._ensure_entity_tables()

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()
        data_json = entity.model_dump_json()
        entity_type = entity.descriptor.entity_type.value if entity.descriptor else "UNKNOWN"

        cursor.execute(
            """
            INSERT OR REPLACE INTO entities (id, entity_type, data_json, created_at, updated_at)
            VALUES (?, ?, ?,
                COALESCE((SELECT created_at FROM entities WHERE id = ?), ?),
                ?)
            """,
            (entity.id, entity_type, data_json, entity.id, now, now),
        )

        conn.commit()
        conn.close()

    def update_relationship(self, relationship: Relationship) -> None:
        """Insert or update a relationship in the database."""
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")

        self._ensure_entity_tables()

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()
        data_json = json.dumps(
            {
                "visibility": relationship.visibility.value if hasattr(relationship, "visibility") else "public",
                "metadata": relationship.metadata_dict if hasattr(relationship, "metadata_dict") else relationship.metadata,
            }
        )

        cursor.execute(
            """
            INSERT OR REPLACE INTO relationships
            (id, source_id, target_id, relationship_type, strength, description, data_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?,
                COALESCE((SELECT created_at FROM relationships WHERE id = ?), ?),
                ?)
            """,
            (
                relationship.id,
                relationship.source_id,
                relationship.target_id,
                relationship.relationship_type.value,
                relationship.strength,
                relationship.description,
                data_json,
                relationship.id,
                now,
                now,
            ),
        )

        conn.commit()
        conn.close()

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
        from .models import generate_intuitive_id

        migration = SchemaMigration(
            id=generate_intuitive_id("MIG"),
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