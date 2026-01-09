"""
File I/O Manager for Forge 3.0.

Handles file system operations for staging, source documents,
and project data management.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# ============================================================================
# File Manager
# ============================================================================


class FileManager:
    """Manages file system operations for a project.
    
    Handles:
    - Staging directory for extracted data
    - Source document storage and retrieval
    - JSON file operations for staging artifacts
    
    Usage:
        fm = FileManager(project_path)
        
        # Write staging JSON
        fm.write_staging_json("entities_staging.json", entities_data)
        
        # Read staging JSON
        data = fm.read_staging_json("entities_staging.json")
    """
    
    STAGING_DIR = "staging"
    LOGS_DIR = "logs"
    SOURCES_DIR = "staging/sources"
    
    def __init__(self, project_path: str | Path):
        """Initialize the file manager.
        
        Args:
            project_path: Root path of the project directory
        """
        self.project_path = Path(project_path)
    
    @property
    def staging_path(self) -> Path:
        return self.project_path / self.STAGING_DIR
    
    @property
    def sources_path(self) -> Path:
        return self.project_path / self.SOURCES_DIR
    
    @property
    def logs_path(self) -> Path:
        return self.project_path / self.LOGS_DIR
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.staging_path.mkdir(parents=True, exist_ok=True)
        self.sources_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
    
    # ========== Staging Operations ==========
    
    def write_staging_json(
        self,
        filename: str,
        data: Any,
        pretty: bool = True,
    ) -> Path:
        """Write data to a staging JSON file.
        
        Args:
            filename: Name of the file (e.g., "entities_staging.json")
            data: Data to serialize to JSON
            pretty: Whether to format with indentation
            
        Returns:
            Path to the written file
        """
        self.ensure_directories()
        
        filepath = self.staging_path / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, default=str)
        
        return filepath
    
    def read_staging_json(self, filename: str) -> Any:
        """Read data from a staging JSON file.
        
        Args:
            filename: Name of the file to read
            
        Returns:
            Parsed JSON data
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        filepath = self.staging_path / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Staging file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def staging_file_exists(self, filename: str) -> bool:
        """Check if a staging file exists."""
        return (self.staging_path / filename).exists()
    
    def list_staging_files(self, pattern: str = "*.json") -> list[Path]:
        """List staging files matching a pattern."""
        return list(self.staging_path.glob(pattern))
    
    def clear_staging(self) -> None:
        """Remove all files from the staging directory."""
        for file in self.staging_path.iterdir():
            if file.is_file():
                file.unlink()
    
    def archive_staging(self, archive_name: str | None = None) -> Path:
        """Archive current staging files with timestamp.
        
        Args:
            archive_name: Optional custom archive name
            
        Returns:
            Path to the archive directory
        """
        if archive_name is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            archive_name = f"staging_archive_{timestamp}"
        
        archive_path = self.staging_path / archive_name
        archive_path.mkdir(exist_ok=True)
        
        for file in self.staging_path.iterdir():
            if file.is_file():
                shutil.move(str(file), str(archive_path / file.name))
        
        return archive_path
    
    # ========== Source Document Operations ==========
    
    def save_source_document(
        self,
        filename: str,
        content: str | bytes,
    ) -> Path:
        """Save a source document to the sources directory.
        
        Args:
            filename: Name for the file
            content: Text or binary content
            
        Returns:
            Path to the saved file
        """
        self.ensure_directories()
        
        filepath = self.sources_path / filename
        
        if isinstance(content, bytes):
            with open(filepath, "wb") as f:
                f.write(content)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        
        return filepath
    
    def get_source_document(self, filename: str) -> str:
        """Read a source document.
        
        Args:
            filename: Name of the file
            
        Returns:
            File contents as string
        """
        filepath = self.sources_path / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Source document not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    
    def list_source_documents(self) -> list[Path]:
        """List all source documents."""
        if not self.sources_path.exists():
            return []
        return [f for f in self.sources_path.iterdir() if f.is_file()]
    
    def delete_source_document(self, filename: str) -> bool:
        """Delete a source document.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if deleted, False if not found
        """
        filepath = self.sources_path / filename
        
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    # ========== Log Operations ==========
    
    def write_log(
        self,
        log_name: str,
        content: str,
        append: bool = True,
    ) -> Path:
        """Write to a log file.
        
        Args:
            log_name: Name of the log file
            content: Content to write
            append: Whether to append or overwrite
            
        Returns:
            Path to the log file
        """
        self.ensure_directories()
        
        filepath = self.logs_path / log_name
        mode = "a" if append else "w"
        
        with open(filepath, mode, encoding="utf-8") as f:
            timestamp = datetime.now(UTC).isoformat()
            f.write(f"[{timestamp}] {content}\n")
        
        return filepath
    
    def read_log(self, log_name: str, lines: int | None = None) -> str:
        """Read a log file.
        
        Args:
            log_name: Name of the log file
            lines: Optional number of lines from end to read
            
        Returns:
            Log contents
        """
        filepath = self.logs_path / log_name
        
        if not filepath.exists():
            return ""
        
        with open(filepath, "r", encoding="utf-8") as f:
            if lines is None:
                return f.read()
            else:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
    
    # ========== Generic File Operations ==========
    
    def read_json(self, relative_path: str) -> Any:
        """Read a JSON file relative to project root."""
        filepath = self.project_path / relative_path
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def write_json(
        self,
        relative_path: str,
        data: Any,
        pretty: bool = True,
    ) -> Path:
        """Write a JSON file relative to project root."""
        filepath = self.project_path / relative_path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, default=str)
        
        return filepath
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists relative to project root."""
        return (self.project_path / relative_path).exists()
    
    def delete_file(self, relative_path: str) -> bool:
        """Delete a file relative to project root."""
        filepath = self.project_path / relative_path
        
        if filepath.exists():
            filepath.unlink()
            return True
        return False
