"""Harvester CLI - Entity extraction from documents.

Updated to use the new Multi-Agent Orchestrator.

Usage:
    python -m pyscrai_forge.src process ./document.txt
    python -m pyscrai_forge.src process ./history.txt --genre historical --output review_packet.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

# Load .env early for provider selection
load_dotenv()
from rich.console import Console
from rich.panel import Panel

from pyscrai_core import ProjectManifest
from pyscrai_forge.agents.manager import ForgeManager
from pyscrai_forge.prompts.core import Genre
from pyscrai_core.llm_interface.provider_factory import (
    create_provider_from_env,
    get_default_model_from_env,
    get_default_provider_name,
)

# Initialize Typer app
app = typer.Typer(
    name="forge",
    help="PyScrAI|Forge CLI",
    add_completion=False,
)
# --- GUI Command ---
@app.command("gui")
def launch_gui():
    """Launch the PyScrAI|Forge main application (landing page)."""
    from pyscrai_forge.src.forge import main as reviewer_main
    reviewer_main()

# --- ARCHITECT Command ---
@app.command("architect")
def launch_architect(
    project: Annotated[Path | None, typer.Option("--project", "-p", help="Path to existing project")] = None,
):
    """Launch the ForgeManager (Interactive Sorcerer Mode)."""
    console.print(Panel("Initializing ForgeManager...", style="cyan"))
    
    # Setup Provider
    provider, model = create_provider_from_env()
    
    # Start Loop
    manager = ForgeManager(provider, project_path=project)
    
    try:
        asyncio.run(manager.interactive_chat())
    except KeyboardInterrupt:
        console.print("\n[yellow]ForgeManager session terminated.[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal Error: {e}[/red]")

console = Console()
DEFAULT_PROVIDER = get_default_provider_name()
DEFAULT_MODEL = get_default_model_from_env() or ""


async def _process_file(
    file_path: Path,
    genre: Genre,
    model: str,
    output: Path | None,
    project_path: Path | None = None,
) -> str:
    """Internal async function for processing a single file."""
    provider, env_model = create_provider_from_env()
    selected_model = model or env_model or DEFAULT_MODEL
    
    # Try to load manifest
    manifest = None
    if project_path:
        manifest_path = project_path / "project.json"
        if manifest_path.exists():
            try:
                manifest = ProjectManifest.from_json(manifest_path.read_text(encoding="utf-8"))
                console.print(f"[green]Loaded Manifest from {project_path}[/green]")
            except Exception as e:
                console.print(f"[yellow]Failed to load manifest: {e}[/yellow]")
    
    # Fallback/Default
    if manifest is None:
        manifest = ProjectManifest(name="CLI Session")
    
    # Read text first
    from pyscrai_forge.src.extractor import FileExtractor
    extractor = FileExtractor()
    try:
        extraction_result = await extractor.extract_from_file(str(file_path), genre=genre)
        text = extraction_result.text
    except Exception as e:
        console.print(f"[red]Extraction failed: {e}[/red]")
        raise
    
    # Create temporary project if none provided
    from pathlib import Path
    from pyscrai_core import ProjectController
    temp_project_path = None
    if project_path:
        temp_project_path = project_path
    else:
        # Create a temporary project for the extraction
        temp_project_path = Path.cwd() / ".temp_extraction_project"
        if not temp_project_path.exists():
            temp_controller = ProjectController(temp_project_path)
            temp_controller.create_project(manifest)
    
    async with provider:
        manager = ForgeManager(provider, project_path=temp_project_path)
        console.print(f"Starting extraction pipeline on {file_path.name}...")
        result_path = await manager.run_extraction_pipeline(
            text=text,
            genre=genre,
            output_path=output
        )
        
        return result_path


@app.command("process")
def process_file(
    file: Annotated[Path, typer.Argument(help="Path to text file to process")] = Path("data/harvester/input/sample_historical.txt"),
    genre: Annotated[Genre, typer.Option("--genre", "-g", help="Document genre")] = Genre.GENERIC,
    model: Annotated[str | None, typer.Option("--model", "-m", help="LLM model to use")] = DEFAULT_MODEL or None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output JSON file")] = None,
    project: Annotated[Path | None, typer.Option("--project", "-p", help="Path to Project (for schema)")] = None,
) -> None:
    """Process a single text file and extract entities."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]File:[/bold] {file}\n"
        f"[bold]Genre:[/bold] {genre.value}\n"
        f"[bold]Model:[/bold] {model or 'auto'}",
        title="Agentic Harvester",
        border_style="blue",
    ))
    
    out_path = asyncio.run(_process_file(file, genre, model, output, project))
    
    console.print(Panel(
        f"Review Packet ready at:\n[bold]{out_path}[/bold]\n\n"
        f"Run forge UI to validate:\n"
        f"python -m pyscrai_forge.src.forge {out_path}",
        title="Extraction Complete",
        border_style="green",
    ))


# Module entry point
def main() -> None:
    """Entry point for python -m pyscrai_forge.src"""
    app()


if __name__ == "__main__":
    main()