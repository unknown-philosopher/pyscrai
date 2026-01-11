# setup.py - UNIFIED EXTRACT, CONTROL & COMPUTE (Python 3.12+)
from setuptools import setup, find_packages

setup(
    name="PyScrAI_Forge",
    version="3.0.0",
    description="PyScrAI|Forge - Unified 3.12 Cockpit & CUDA Engine",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # --- UI & REACTIVE ---
        "flet>=0.24.0",
        "FletXr==0.1.3",
        
        # --- VECTOR & ML ENGINE (3.12 Compatible) ---
        "torch>=2.2.0",           # Native 3.12 CUDA support
        "qdrant-client[fastembed-gpu]>=1.7.0", # Replaces FAISS with GPU vector search
        "transformers>=4.38.0",   # Latest local LLM support
        "bitsandbytes>=0.42.0",   # 4-bit quantization for your 4060
        "accelerate>=0.27.0",
        
        # --- DATABASE & ANALYTICS ---
        "duckdb>=0.10.0",
        "pydantic>=2.0.0",
        "networkx>=3.2",
        "plotly>=5.18.0",

        # --- DOCUMENT & LOGIC ---
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "jinja2>=3.0.0",
        "pypdf>=4.0.0",
        "beautifulsoup4>=4.12.0",
        "rich>=13.0.0",
    ],
    python_requires=">=3.12",
)