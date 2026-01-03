# pyscrai_forge/harvester/converters/docx_converter.py
from pathlib import Path
from typing import Dict
import docx
from .registry import BaseConverter, ConversionResult

class DOCXConverter(BaseConverter):
    """Converter for DOCX files using python-docx."""

    def convert(self, file_path: Path) -> ConversionResult:
        try:
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)

            text = '\n'.join(full_text)

            metadata = {}
            core_props = doc.core_properties
            if core_props.title:
                metadata['title'] = core_props.title
            if core_props.author:
                metadata['author'] = core_props.author
            if core_props.created:
                metadata['created'] = str(core_props.created)
            if core_props.modified:
                metadata['modified'] = str(core_props.modified)

            return ConversionResult(text=text, metadata=metadata)
        except Exception as e:
            raise e
