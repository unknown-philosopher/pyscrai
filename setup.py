from setuptools import setup, find_packages

setup(
    name="PyScrAI_Forge",
    version="3.0.0",
    description="PyScrAI|Forge - Worldbuilding and entity extraction toolkit",
    author="TylerHamilton",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Core data modeling and validation
        "pydantic>=2.0.0",
        
        # Async HTTP client (for LLM providers)
        "httpx>=0.25.0",
        
        # Environment variables
        "python-dotenv>=1.0.0",
        
        # Vector search (optional - graceful fallback if unavailable)
        "sqlite-vec>=0.1.0",
        
        # Sentence embeddings (for memory vectorization)
        "sentence-transformers>=2.2.0",
        
        # Graph analysis (for Loom phase)
        "networkx>=3.0",
        
        # CLI and rich output
        "typer>=0.9.0",
        "rich>=13.0.0",
        
        # YAML support for prefabs/prompts
        "pyyaml>=6.0.0",
        
        # Jinja2 for prompt templates 
        "jinja2>=3.0.0",
        
        # Document processing
        "pypdf>=3.0.0",
        "beautifulsoup4>=4.12.0",
        "markdown>=3.4.0",
        "python-docx>=0.8.11",
        "pytesseract>=0.3.10",
        "Pillow>=8.0.0",
        
        # NiceGUI frontend (native desktop mode)
        "nicegui>=1.4.0",
        "pywebview>=4.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
        ],
        "cuda": [
            "torch>=2.0.0",
            "torchvision>=0.15.0",
            "torchaudio>=2.0.0",
        ],

        "all": [
            # Dev dependencies
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            # CUDA dependencies
            "torch>=2.0.0",
            "torchvision>=0.15.0",
            "torchaudio>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "forge = forge.app.main:main",
            "forge-legacy = pyscrai_forge.src.cli:main",
        ],
    },
    python_requires=">=3.10",
    package_dir={"": "."},
)
