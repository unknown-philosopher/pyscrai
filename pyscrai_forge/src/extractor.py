"""File extraction utility for the Harvester.

Handles extracting text from various file formats (.txt, .pdf, .md, .html).
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from pyscrai_forge.src.prompts import Genre

# Optional imports for file handling
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import markdown
except ImportError:
    markdown = None


@dataclass
class ExtractionResult:
    """Container for the result of file extraction."""
    source_file: str
    text: str
    metadata: Optional[dict] = None


class FileExtractor:
    """Extracts raw text from supported file formats."""

    async def extract_from_file(
        self,
        file_path: str,
        genre: Genre = Genre.GENERIC,
        entity_types: List[str] | None = None,
    ) -> ExtractionResult:
        """Extract entities from a file.

        Currently supports: .txt, .pdf, .md, .html
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = file_path_obj.suffix.lower()

        if extension == ".txt":
            return await self._extract_txt(file_path_obj)
        elif extension == ".pdf":
            return await self._extract_pdf(file_path_obj)
        elif extension == ".md":
            return await self._extract_md(file_path_obj)
        elif extension in [".html", ".htm"]:
            return await self._extract_html(file_path_obj)
        else:
            raise ValueError(f"Unsupported file format: {extension}")

    async def _extract_txt(self, path: Path) -> ExtractionResult:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return ExtractionResult(source_file=str(path), text=text)

    async def _extract_pdf(self, path: Path) -> ExtractionResult:
        if not pypdf:
            raise ImportError("pypdf is required for PDF extraction. Install it with `pip install pypdf`.")

        text = ""
        metadata = {}

        # pypdf operations can be blocking, run in executor
        def _read_pdf():
            nonlocal text, metadata
            with open(path, "rb") as f:
                reader = pypdf.PdfReader(f)
                if reader.metadata:
                    metadata = dict(reader.metadata)
                for page in reader.pages:
                    text += page.extract_text() + "\n"

        await asyncio.to_thread(_read_pdf)
        return ExtractionResult(source_file=str(path), text=text, metadata=metadata)

    async def _extract_md(self, path: Path) -> ExtractionResult:
        # We return raw markdown as it provides good context for LLMs.
        # No extra dependencies needed for raw read.
        with open(path, "r", encoding="utf-8") as f:
            md_content = f.read()

        return ExtractionResult(source_file=str(path), text=md_content)

    async def _extract_html(self, path: Path) -> ExtractionResult:
        if not BeautifulSoup:
            raise ImportError("beautifulsoup4 is required for HTML extraction. Install it with `pip install beautifulsoup4`.")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        title = soup.title.string if soup.title else None
        metadata = {"title": title} if title else None

        return ExtractionResult(source_file=str(path), text=text, metadata=metadata)
