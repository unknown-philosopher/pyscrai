# PyScrAI|Forge Project Structure

This document provides a comprehensive guide to the file structure and organization of the PyScrAI|Forge module.

## Overview

PyScrAI|Forge is organized into three main directories:
- **`agents/`** - Multi-agent Harvester system (Scout, Analyst, Validator, Reviewer, Manager)
- **`src/`** - Main application code (CLI, GUI, utilities)
- **`docs/`** - Documentation and development plans

---

## Directory Structure

```
pyscrai_forge/
├── agents/              # Harvester agent implementations
├── docs/                # Documentation
└── src/                 # Main application source code
    ├── converters/      # File format converters
    └── ui/              # GUI components
        ├── dialogs/     # Modal dialogs
        ├── widgets/     # Reusable UI widgets
        └── windows/     # Standalone windows
```

---

## Core Source Files (`src/`)

### Entry Points

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Module exports and public API | ✅ Active | Exports `ReviewerApp`, storage functions, prompts |
| `__main__.py` | Module execution entry point | ✅ Active | Allows `python -m pyscrai_forge.src` → calls `cli.main()` |

### CLI & Processing

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `cli.py` | Command-line interface (Typer) | ✅ Active | Entry point for `forge` command. Handles `forge gui` and `forge process` |
| `extractor.py` | File extraction utility | ✅ Active | Used by `cli.py` to extract text from .txt, .pdf, .md, .html files |
| `reviewer_cli.py` | CLI wrapper for Reviewer GUI | ⚠️ **UNUSED** | Not imported anywhere. Redundant with `cli.py`'s `forge gui` command |

### Main Application

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `forge.py` | Main GUI application controller | ✅ Active | **Primary UI controller** (1260 lines). Handles 3-state UI (Landing, Dashboard, Component Editor), project management, entity/relationship editing, import/export, validation |

**Note:** `forge.py` has evolved from a simple review tool into the main application controller. Consider refactoring (see recommendations below).

### Data & Storage

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `storage.py` | Database operations layer | ✅ Active | SQLite interface for entities/relationships. Used by `forge.py` for commit operations |
| `prompts.py` | LLM prompt templates | ✅ Active | Genre-aware prompts for Scout, Analyst, and Relationship extraction. Used by agents |
| `user_config.py` | User preferences/config | ✅ Active | Manages recent projects, window geometry, preferences. Used by `forge.py` |

---

## Converters (`src/converters/`)

File format conversion system for importing documents.

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Module exports | ✅ Active | Exports registry |
| `registry.py` | Converter registry/dispatcher | ✅ Active | Routes file extensions to appropriate converters. Used by `ui/import_dialog.py` |
| `pdf_converter.py` | PDF text extraction | ✅ Active | Registered for `.pdf` files |
| `html_converter.py` | HTML text extraction | ✅ Active | Registered for `.html`, `.htm` files |
| `docx_converter.py` | Word document extraction | ✅ Active | Registered for `.docx` files |
| `ocr_converter.py` | Image OCR extraction | ✅ Active | Registered for `.png`, `.jpg`, `.jpeg` files |

**Note:** Converters are registered in `ui/import_dialog.py`. Consider moving registration to a central location.

---

## UI Components (`src/ui/`)

### Main UI Files

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Module exports | ✅ Active | Empty (could export main components) |
| `entity_editor.py` | Entity editing dialog | ✅ Active | Tabbed editor for entity components. Used by `forge.py` |
| `relationship_editor.py` | Relationship editing dialog | ✅ Active | Dialog for editing relationships. Used by `forge.py` |
| `import_dialog.py` | File import dialog | ✅ Active | Handles file selection, conversion, preview. Used by `forge.py` |
| `schema_widgets.py` | Schema-related widgets | ✅ Active | Reusable widgets for schema editing |

### Dialogs (`ui/dialogs/`)

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Module exports | ✅ Active | - |
| `project_wizard.py` | New project creation wizard | ✅ Active | Used by `forge.py` for `File → New Project` |
| `query_dialog.py` | Query/search dialog | ✅ Active | - |
| `schema_field_dialog.py` | Schema field editor | ✅ Active | - |

### Widgets (`ui/widgets/`)

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Module exports | ✅ Active | - |
| `landing_page.py` | Landing page widget | ✅ Active | Used by `forge.py` for LANDING state |
| `project_dashboard.py` | Project dashboard widget | ✅ Active | Used by `forge.py` for DASHBOARD state |
| `schema_builder.py` | Schema builder widget | ✅ Active | - |
| `stats_panel.py` | Statistics panel widget | ✅ Active | - |
| `dependency_manager.py` | Dependency management widget | ✅ Active | - |

### Windows (`ui/windows/`)

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Module exports | ✅ Active | - |
| `db_explorer.py` | Database explorer window | ✅ Active | Used by `forge.py` for `Data → Database Explorer` |
| `file_browser.py` | File browser window | ✅ Active | Used by `forge.py` for `Project → Open Project Files` |
| `project_manager.py` | Project settings window | ✅ Active | Used by `forge.py` for `Project → Project Settings` |

---

## Agents (`agents/`)

Multi-agent Harvester system for entity extraction.

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `manager.py` | Harvester orchestrator | ✅ Active | Coordinates Scout, Analyst, Validator, Reviewer agents. Used by `cli.py` and `forge.py` |
| `scout.py` | Entity discovery agent | ✅ Active | Discovers entities in text. Used by `manager.py` |
| `analyst.py` | Data mining agent | ✅ Active | Extracts detailed entity data. Used by `manager.py` |
| `validator.py` | Validation agent | ✅ Active | Validates entities/relationships. Used by `manager.py` |
| `forge.py` | Review agent | ✅ Active | Reviews extraction results. Used by `manager.py` |
| `models.py` | Agent data models | ✅ Active | Shared models for agents |

---

## Documentation (`docs/`)

| Directory/File | Purpose |
|---------------|---------|
| `forge_user_guide.md` | Comprehensive user and developer guide |
| `harvester_agents.md` | Documentation for Harvester agents |
| `project_structure.md` | This file - project structure reference |
| `notes.md` | Development notes |
| `dev_plans/` | Development planning documents |
| `dev_plans/completed/` | Completed phase retrospectives |
| `dev_plans/tkinter_dev/` | Tkinter development guides |

---

## File Usage Summary

### ✅ Actively Used Files
- All files in `agents/`, `converters/`, `ui/` are actively used
- Core files: `cli.py`, `extractor.py`, `forge.py`, `storage.py`, `prompts.py`, `user_config.py`

### ⚠️ Potentially Unused/Redundant
- **`reviewer_cli.py`** - Not imported anywhere. Functionality covered by `cli.py`'s `forge gui` command

### 📊 File Size & Complexity
- **`forge.py`** - 1260 lines (largest file) - Main application controller, needs refactoring consideration
- **`storage.py`** - 349 lines - Well-organized database layer
- **`prompts.py`** - 301 lines - Prompt templates

---

## Key Dependencies

### Internal Dependencies
- `forge.py` imports: `storage`, `user_config`, all UI components, agents
- `cli.py` imports: `extractor`, `reviewer` (for GUI), `agents.manager`
- `import_dialog.py` imports: all converters

### External Dependencies
- **Tkinter** - GUI framework (built-in)
- **Typer** - CLI framework
- **Pydantic** - Data validation
- **SQLite3** - Database (built-in)
- **Rich** - Terminal formatting

---

## Entry Points

1. **CLI**: `forge` command (via `setup.py` entry_points) → `cli.main()`
   - `forge gui` → launches `forge.py`
   - `forge process` → runs Harvester pipeline

2. **Module**: `python -m pyscrai_forge.src` → `__main__.py` → `cli.main()`

3. **Direct**: `python -m pyscrai_forge.src.reviewer` → launches GUI directly

---

## Recommendations

For detailed refactoring recommendations, optimization opportunities, and quality-of-life improvements, see:

- **[Refactoring Recommendations](REFACTORING_RECOMMENDATIONS.md)**: Comprehensive guide to refactoring `forge.py`, removing unused code, and improving code quality.

