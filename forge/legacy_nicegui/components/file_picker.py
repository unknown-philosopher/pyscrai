"""
File Picker Component.

Native file dialog wrapper for document uploads.
Supports text files, PDFs, and other document formats.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from nicegui import ui

from forge.utils.logging import get_logger

logger = get_logger("frontend.file_picker")


SUPPORTED_EXTENSIONS = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".html": "text/html",
    ".htm": "text/html",
}


class FilePicker:
    """Native file picker component for document uploads."""
    
    def __init__(
        self,
        on_upload: Callable[[Path, bytes], None] | None = None,
        multiple: bool = True,
        label: str = "Upload Documents",
    ) -> None:
        """Initialize the file picker.
        
        Args:
            on_upload: Callback when file(s) are uploaded (path, content)
            multiple: Allow multiple file selection
            label: Button label text
        """
        self.on_upload = on_upload
        self.multiple = multiple
        self.label = label
        self._uploaded_files: list[Path] = []
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the file picker UI."""
        with ui.column().classes("w-full"):
            # Upload area
            self._upload = ui.upload(
                label=self.label,
                multiple=self.multiple,
                on_upload=self._handle_upload,
            ).classes("w-full").props("accept='.txt,.md,.pdf,.docx,.doc,.html'")
            
            # Uploaded files list
            self._files_container = ui.column().classes("w-full q-mt-sm")
    
    async def _handle_upload(self, e) -> None:
        """Handle file upload event."""
        if not e.content:
            return
        
        try:
            # Get file info
            filename = e.name
            content = e.content.read()
            
            # Create a Path object (for display purposes)
            path = Path(filename)
            
            logger.info(f"File uploaded: {filename} ({len(content)} bytes)")
            
            # Add to list
            self._uploaded_files.append(path)
            self._update_file_list()
            
            # Call callback
            if self.on_upload:
                self.on_upload(path, content)
            
            ui.notify(f"Uploaded: {filename}", type="positive")
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            ui.notify(f"Upload failed: {e}", type="negative")
    
    def _update_file_list(self) -> None:
        """Update the displayed list of uploaded files."""
        self._files_container.clear()
        
        with self._files_container:
            for path in self._uploaded_files:
                with ui.row().classes("items-center q-gutter-sm"):
                    ui.icon("description", size="sm").classes("text-grey-5")
                    ui.label(path.name).classes("text-body2")
                    ui.button(
                        icon="close",
                        color="negative",
                    ).props("flat round size=xs").on(
                        "click",
                        lambda p=path: self._remove_file(p)
                    )
    
    def _remove_file(self, path: Path) -> None:
        """Remove a file from the uploaded list."""
        if path in self._uploaded_files:
            self._uploaded_files.remove(path)
            self._update_file_list()
            logger.debug(f"Removed file: {path.name}")
    
    def get_files(self) -> list[Path]:
        """Get list of uploaded file paths."""
        return self._uploaded_files.copy()
    
    def clear(self) -> None:
        """Clear all uploaded files."""
        self._uploaded_files.clear()
        self._update_file_list()
        self._upload.reset()
