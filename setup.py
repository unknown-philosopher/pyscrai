from setuptools import setup, find_packages

setup(
    name="pyscrai-forge",
    version="0.9.8",
    description="PyScrAI|Forge - Worldbuilding and entity extraction toolkit",
    author="Your Name",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Core data modeling and validation
        "pydantic>=2.0.0",
        # Async HTTP client (for LLM providers)
        "httpx>=0.25.0",
        # Environment variables
        "python-dotenv>=1.0.0",
        # Vector database (semantic memory)
        "chromadb>=0.4.0",
        # Sentence embeddings (for memory vectorization)
        "sentence-transformers>=2.2.0",
        # CLI tools (for Harvester)
        "typer>=0.9.0",
        "rich>=13.0.0",
        # GUI - Tkinter is built-in, Dear PyGui for advanced editing
        "dearpygui>=1.10.0",
        # Web framework (for Environment Editor API)
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        # LangChain Adapter
        "langchain-core>=0.1.0",
        # Document processing
        "pypdf>=3.0.0",
        "beautifulsoup4>=4.12.0",
        "markdown>=3.4.0",
        "python-docx>=0.8.11",
        "pytesseract>=0.3.10",
        "Pillow>=8.0.0",
        # Development dependencies (optional, can be moved to extras_require)
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        # UI Theme
        "sv-ttk>=2.6.0",
    ],
    entry_points={
        "console_scripts": [
            "forge = pyscrai_forge.src.cli:main",
            "pyscrai-engine = pyscrai_engine.__main__:main",
        ],
    },
    python_requires=">=3.8",
    package_dir={"": "."},
)