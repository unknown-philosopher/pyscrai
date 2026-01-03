"""File format converters for PyScrAI|Forge.

This module provides converters for various file formats (PDF, HTML, DOCX, OCR)
and a centralized registry for managing them.
"""

from .registry import FormatRegistry, ConversionResult, BaseConverter

# Import converter classes
from .pdf_converter import PDFConverter
from .html_converter import HTMLConverter
from .docx_converter import DOCXConverter
from .ocr_converter import OCRConverter


def create_registry() -> FormatRegistry:
    """Create and configure the converter registry with all default converters.
    
    This function registers all available converters with their file extensions.
    It serves as the single source of truth for converter registration.
    
    Returns:
        A FormatRegistry instance with all converters registered
        
    Example:
        >>> registry = create_registry()
        >>> result = registry.convert(Path("document.pdf"))
    """
    registry = FormatRegistry()
    
    # Register PDF converter
    registry.register('.pdf', PDFConverter)
    
    # Register HTML converters
    registry.register('.html', HTMLConverter)
    registry.register('.htm', HTMLConverter)
    
    # Register Word document converter
    registry.register('.docx', DOCXConverter)
    
    # Register OCR converters for images
    registry.register('.png', OCRConverter)
    registry.register('.jpg', OCRConverter)
    registry.register('.jpeg', OCRConverter)
    
    return registry


__all__ = [
    'FormatRegistry',
    'ConversionResult',
    'BaseConverter',
    'create_registry',
    'PDFConverter',
    'HTMLConverter',
    'DOCXConverter',
    'OCRConverter',
]
