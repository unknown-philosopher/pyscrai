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

console = Console()
DEFAULT_PROVIDER = get_default_provider_name()
DEFAULT_MODEL = get_default_model_from_env() or ""


async def _process_file(
    file_path: Path,
    genre: Genre,
    model: str,
    output: Path | None,
    project_path: Path | None = None,
    verbose: bool = False,
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
            output_path=output,
            verbose=verbose
        )
        
        return result_path


@app.command("process")
def process_file(
    file: Annotated[Path, typer.Argument(help="Path to text file to process")] = Path("data/harvester/input/sample_historical.txt"),
    genre: Annotated[Genre, typer.Option("--genre", "-g", help="Document genre")] = Genre.GENERIC,
    model: Annotated[str | None, typer.Option("--model", "-m", help="LLM model to use")] = DEFAULT_MODEL or None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output JSON file")] = None,
    project: Annotated[Path | None, typer.Option("--project", "-p", help="Path to Project (for schema)")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output (show prompts and responses)")] = False,
) -> None:
    """Process a single text file and extract entities (automated)."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]File:[/bold] {file}\n"
        f"[bold]Genre:[/bold] {genre.value}\n"
        f"[bold]Model:[/bold] {model or 'auto'}\n"
        f"[bold]Verbose:[/bold] {verbose}",
        title="Entity Extraction",
        border_style="blue",
    ))
    
    out_path = asyncio.run(_process_file(file, genre, model, output, project, verbose))
    
    console.print(Panel(
        f"Review Packet ready at:\n[bold]{out_path}[/bold]\n\n"
        f"Run forge UI to review and refine:\n"
        f"forge gui",
        title="Extraction Complete",
        border_style="green",
    ))


# --- ENGINE Commands ---
@app.command("run")
def run_simulation(
    project: Annotated[Path, typer.Argument(help="Path to project directory")],
    max_turns: Annotated[int, typer.Option("--turns", "-t", help="Maximum turns to run")] = 100,
):
    """Run a simulation on a Forge project."""
    from pyscrai_engine import SimulationEngine
    
    if not project.exists():
        console.print(f"[red]Error:[/red] Project not found: {project}")
        raise typer.Exit(1)
        
    console.print(Panel(
        f"[bold]Project:[/bold] {project}\n"
        f"[bold]Max Turns:[/bold] {max_turns}",
        title="PyScrAI Engine - Simulation Run",
        border_style="cyan",
    ))
    
    try:
        engine = SimulationEngine(project)
        engine.initialize()
        engine.run(max_turns=max_turns)
        
        console.print(Panel(
            f"[green]Simulation completed successfully![/green]\n"
            f"Total turns: {engine.current_turn}\n"
            f"Events processed: {len(engine.turn_history)}",
            title="Simulation Complete",
            border_style="green",
        ))
        
    except Exception as e:
        console.print(f"[red]Simulation error: {e}[/red]")
        raise typer.Exit(1)


@app.command("step")
def step_simulation(
    project: Annotated[Path, typer.Argument(help="Path to project directory")],
):
    """Execute a single turn in a simulation."""
    from pyscrai_engine import SimulationEngine
    
    if not project.exists():
        console.print(f"[red]Error:[/red] Project not found: {project}")
        raise typer.Exit(1)
        
    try:
        engine = SimulationEngine(project)
        engine.initialize()
        
        console.print(f"[cyan]Executing turn {engine.current_turn + 1}...[/cyan]")
        turn_result = engine.step()
        
        console.print(Panel(
            f"[green]Turn {turn_result.turn_number} completed[/green]\n"
            f"Events: {len(turn_result.events)}\n"
            f"Narrative entries: {len(turn_result.narrative)}",
            title="Turn Complete",
            border_style="green",
        ))
        
        # Display narrative
        if turn_result.narrative:
            console.print("\n[bold]Turn Narrative:[/bold]")
            for entry in turn_result.narrative:
                console.print(f"  • {entry.text}")
        
    except Exception as e:
        console.print(f"[red]Simulation error: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def show_status(
    project: Annotated[Path, typer.Argument(help="Path to project directory")],
):
    """Show current simulation status."""
    from pyscrai_engine import SimulationEngine
    
    if not project.exists():
        console.print(f"[red]Error:[/red] Project not found: {project}")
        raise typer.Exit(1)
        
    try:
        engine = SimulationEngine(project)
        engine.initialize()
        
        # Count entities by type
        from pyscrai_core import EntityType
        actors = engine.get_entities_by_type(EntityType.ACTOR)
        polities = engine.get_entities_by_type(EntityType.POLITY)
        locations = engine.get_entities_by_type(EntityType.LOCATION)
        
        console.print(Panel(
            f"[bold]Project:[/bold] {engine.manifest.name}\n"
            f"[bold]Current Turn:[/bold] {engine.current_turn}\n\n"
            f"[bold]Entities:[/bold]\n"
            f"  • Actors: {len(actors)}\n"
            f"  • Polities: {len(polities)}\n"
            f"  • Locations: {len(locations)}\n"
            f"  • Total: {len(engine.entities)}\n\n"
            f"[bold]Relationships:[/bold] {len(engine.relationships)}",
            title="Simulation Status",
            border_style="cyan",
        ))
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Module entry point
def main() -> None:
    """Entry point for python -m pyscrai_forge.src"""
    app()


if __name__ == "__main__":
    main()