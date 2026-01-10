# pyscrai_forge/harvester/converters/pdf_converter.py
from pathlib import Path
from typing import Dict
from pypdf import PdfReader
from .registry import BaseConverter, ConversionResult

class PDFConverter(BaseConverter):
    """Converter for PDF files using pypdf."""

    def convert(self, file_path: Path) -> ConversionResult:
        try:
            reader = PdfReader(str(file_path))
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

            metadata = {}
            if reader.metadata:
                # Convert PDF metadata to standard dict
                for key, value in reader.metadata.items():
                    # Strip leading slash if present (e.g., /Title -> Title)
                    clean_key = key[1:] if key.startswith('/') else key
                    if value:
                        metadata[clean_key] = str(value)

            return ConversionResult(text=text, metadata=metadata)
        except Exception as e:
            raise e
