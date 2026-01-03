# pyscrai_forge/harvester/converters/ocr_converter.py
from pathlib import Path
from typing import Dict
try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

from .registry import BaseConverter, ConversionResult

class OCRConverter(BaseConverter):
    """Converter for Image files using pytesseract (OCR)."""

    def convert(self, file_path: Path) -> ConversionResult:
        if not HAS_OCR:
             raise ImportError("Pillow and pytesseract are required for OCR conversion.")

        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)

            metadata = {
                'format': image.format,
                'mode': image.mode,
                'size': f"{image.width}x{image.height}"
            }

            return ConversionResult(text=text, metadata=metadata)
        except Exception as e:
            raise e
