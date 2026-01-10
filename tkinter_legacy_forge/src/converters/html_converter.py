# pyscrai_forge/harvester/converters/html_converter.py
from pathlib import Path
from typing import Dict
from bs4 import BeautifulSoup
from .registry import BaseConverter, ConversionResult

class HTMLConverter(BaseConverter):
    """Converter for HTML files using BeautifulSoup."""

    def convert(self, file_path: Path) -> ConversionResult:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()

            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)

            metadata = {}
            if soup.title:
                metadata['title'] = soup.title.string

            # Extract meta tags if needed
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    metadata[name] = content

            return ConversionResult(text=text, metadata=metadata)
        except Exception as e:
            raise e
