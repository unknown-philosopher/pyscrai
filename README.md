# PyScrAI: Worldbuilding AI Platform

**PyScrAI** is a modular, agent-driven platform for creating, extracting, and managing complex simulated worlds. It consists of two main components:

- **`pyscrai_core`**: High-performance Entity-Component-System (ECS) model with project management, events, intentions, and memory systems.
- **`pyscrai_forge`**: Creation tools including multi-agent Harvester pipeline, modern GUI, and CLI for worldbuilding workflows.
- **`pyscrai_engine`**: Not implemented yet, this will be the Engine which will be seeded with the final output of the Forge; turning static data into a fully interactive simulation. 

## Key Features

- **ECS Architecture**: Pydantic-based, schema-flexible data models for Entities, Components, and Relationships.
- **Multi-Agent Harvester**: Automated extraction of structured world data from unstructured text using Scout, Analyst, Validator, and Reviewer agents.
- **Project-First Workflow**: All data and tools are organized around explicit projects for robust data management.
- **Modern GUI**: 3-state UI (Landing Page, Project Dashboard, Active Work View) for seamless project navigation and editing.
- **Provider Agnostic LLM Interface**: Integrates with OpenRouter, local LLMs, and more via `pyscrai_core/llm_interface`.
- **Extensible CLI**: Run extraction, validation, and management tasks from the command line or scripts.

## Documentation

- [**Forge User & Developer Guide**](pyscrai_forge/docs/forge_user_guide.md): Comprehensive guide to using and extending PyScrAI|Forge.
- [**Project Structure Reference**](pyscrai_forge/docs/project_structure.md): Complete file-by-file guide to the PyScrAI|Forge codebase structure and organization.
- [**Harvester Agents Guide**](pyscrai_forge/docs/harvester_agents.md): Details on Scout, Analyst, Validator, Reviewer, and Manager agents.
- [**Current Dev Blueprint**](pyscrai_forge/docs/dev_plans/phase_1-3.md): The authoritative roadmap for ongoing and future development phases.
- [**Completed Dev Plans**](pyscrai_forge/docs/dev_plans/completed/): Detailed retrospectives on completed development phases.
- [**Tkinter Development Guides**](pyscrai_forge/docs/dev_plans/tkinter_dev/): Practical guides and tips for GUI development with Tkinter.

## Quick Start

### Prerequisites
- Python 3.10+
- `pip`

### Installation

```bash
pip install -e .
```

### Launching the Application

- **GUI (Recommended):**
  ```bash
  forge gui
  ```
  Opens the main PyScrAI|Forge application (Landing Page, Project Dashboard, and tools).

- **CLI Harvester:**
  ```bash
  forge process <your_text_file.txt> --genre <genre> --output <output.json>
  ```
  Extracts entities from text using the multi-agent pipeline.

### Running Tests
(Not implemented)
```bash
pytest
```

## Project Structure

- `pyscrai_core/` — Simulation engine: Entities, Components, Events, Project Manifest, Memory, Intentions.
  - `llm_interface/` — LLM provider adapters (OpenRouter, local LLMs, etc.).
- `pyscrai_forge/` — Creation tools: Harvester agents, GUI, CLI, project management.
  - `docs/` — Documentation, guides, and dev plans.

## For Developers

- **Entry Points:**
  - `forge gui` — Launch GUI (Tkinter-based, 3-state UI)
  - `forge process` — Run Harvester pipeline from CLI
- **Extending the System:**
  - Add new agents in `pyscrai_forge/agents/`
  - Customize UI widgets in `pyscrai_forge/src/ui/widgets/`
  - Define world schemas in `project.json` within your project folder
  - Extend LLM providers via `pyscrai_core/llm_interface/`

---

For comprehensive usage and development guidance, see the [Forge User & Developer Guide](pyscrai_forge/docs/forge_user_guide.md). For development planning, see the [Current Dev Blueprint](pyscrai_forge/docs/dev_plans/phase_1-3.md) and [Completed Dev Plans](pyscrai_forge/docs/dev_plans/completed/).

