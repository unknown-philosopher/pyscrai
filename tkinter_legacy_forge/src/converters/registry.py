# pyscrai_forge/harvester/converters/registry.py
import os
from pathlib import Path
from typing import Dict, Type, List, Optional
from dataclasses import dataclass

@dataclass
class ConversionResult:
    text: str
    metadata: Dict[str, str]
    error: Optional[str] = None

class BaseConverter:
    """Base class for all file converters."""
    def convert(self, file_path: Path) -> ConversionResult:
        raise NotImplementedError

class FormatRegistry:
    """Registry to manage and dispatch file converters based on file extension."""

    def __init__(self):
        self._converters: Dict[str, Type[BaseConverter]] = {}

    def register(self, extension: str, converter_class: Type[BaseConverter]):
        """Register a converter for a specific file extension (e.g., '.pdf')."""
        self._converters[extension.lower()] = converter_class

    def get_converter(self, file_path: Path) -> Optional[BaseConverter]:
        """Get the appropriate converter instance for the given file path."""
        ext = file_path.suffix.lower()
        converter_cls = self._converters.get(ext)
        if converter_cls:
            return converter_cls()
        return None

    def convert(self, file_path: Path) -> ConversionResult:
        """Convert the file using the registered converter."""
        converter = self.get_converter(file_path)
        if not converter:
            return ConversionResult(
                text="",
                metadata={},
                error=f"No converter found for extension {file_path.suffix}"
            )
        try:
            return converter.convert(file_path)
        except Exception as e:
            return ConversionResult(
                text="",
                metadata={},
                error=str(e)
            )

    def get_supported_formats(self) -> List[str]:
        """Return a list of supported file extensions."""
        return list(self._converters.keys())
