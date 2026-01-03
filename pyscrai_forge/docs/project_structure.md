# PyScrAI|Forge Project Structure

Updated map of the PyScrAI|Forge module after the UI refactor, centralized converters, ConfigManager, dark theme enablement, and reusable column sorting utilities.

## Overview

- **agents/** – Multi-agent Harvester system (Scout, Analyst, Validator, Reviewer, Manager)
- **src/** – Refactored GUI/CLI code with manager-based app architecture, centralized config, dark theme (sv-ttk), and reusable column sorting for Treeviews
- **docs/** – User/developer guides, feature implementation notes, and plans

---

## Directory Structure

```
pyscrai_forge/
├── agents/                  # Harvester agent implementations
├── docs/                    # Documentation & plans
└── src/                     # Main application source code
    ├── app/                 # Refactored application managers
    │   ├── main_app.py      # ReviewerApp coordinator (applies sv-ttk theme)
    │   ├── state_manager.py # AppStateManager (Landing/Dashboard/Editor builders)
    │   ├── menu_manager.py  # Menu construction and state toggles
    │   ├── project_manager.py# ProjectController (load/create/manage projects)
    │   └── data_manager.py  # Data operations for entities/relationships
    ├── converters/          # Converter registry and implementations
    ├── ui/                  # GUI components
    │   ├── dialogs/         # Modal dialogs (project wizard, queries, schema fields)
    │   ├── widgets/         # Reusable widgets (landing, dashboard, treeview_sorter, etc.)
    │   └── windows/         # Standalone windows (DB Explorer, File Browser, Project Manager)
    ├── cli.py               # Typer-based CLI entry (forge gui/process)
    ├── forge.py             # Thin wrapper delegating to app.main_app.ReviewerApp
    ├── config_manager.py    # Singleton ConfigManager
    ├── storage.py           # SQLite persistence layer
    ├── prompts.py           # Prompt templates
    ├── extractor.py         # File extraction utility for CLI
    └── user_config.py       # User preferences (theme, recents, geometry)
```

---

## Core Source Files (`src/`)

### Entry Points

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Module exports and public API | ✅ Active | Exports top-level helpers and ReviewerApp | 
| `__main__.py` | Module execution entry point | ✅ Active | Allows `python -m pyscrai_forge.src` → calls `cli.main()` |
| `cli.py` | Command-line interface (Typer) | ✅ Active | Entry for `forge gui` (launch GUI) and `forge process` (run Harvester) |
| `forge.py` | Wrapper entry for GUI | ✅ Active | Delegates to `app.main_app.ReviewerApp` (kept for backward compatibility) |

### Application Core (`src/app/`)

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `main_app.py` | ReviewerApp coordinator | ✅ Active | Creates Tk root, applies sv-ttk dark/light theme, wires managers, handles lifecycle |
| `state_manager.py` | AppStateManager | ✅ Active | Builds Landing, Dashboard, Component Editor views; owns validation banner and Treeviews with sorting |
| `menu_manager.py` | MenuManager | ✅ Active | Builds menubar, recent projects submenu, and enables/disables items based on project state |
| `project_manager.py` | ProjectController | ✅ Active | Loads/creates projects, manages manifests, recents, and project dialogs |
| `data_manager.py` | DataManager | ✅ Active | Handles entity/relationship CRUD, packet loading, validation status, commit/export hooks |

### Configuration

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `config_manager.py` | Singleton ConfigManager | ✅ Active | Centralized UserConfig access/save/reload for all components |
| `user_config.py` | User preferences/config | ✅ Active | Stores theme preference, recent projects, geometry; uses ConfigManager when present |

### Data & Storage

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `storage.py` | Database operations layer | ✅ Active | SQLite interface for entities/relationships (used by data commit/export flows) |
| `prompts.py` | LLM prompt templates | ✅ Active | Genre-aware prompts for agents |
| `extractor.py` | File extraction utility | ✅ Active | Used by `cli.py` for CLI processing |

### Converters (`src/converters/`)

Centralized registry + converters for imports.

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `__init__.py` | Converter factory | ✅ Active | `create_registry()` registers all converters in one place |
| `registry.py` | Converter registry/dispatcher | ✅ Active | Routes file extensions to converters |
| `pdf_converter.py` | PDF text extraction | ✅ Active | Registered via `create_registry()` |
| `html_converter.py` | HTML text extraction | ✅ Active | Registered via `create_registry()` |
| `docx_converter.py` | Word document extraction | ✅ Active | Registered via `create_registry()` |
| `ocr_converter.py` | Image OCR extraction | ✅ Active | Registered via `create_registry()` |

### UI Components (`src/ui/`)

| Area | Key Files | Notes |
|------|-----------|-------|
| Main UI | `entity_editor.py`, `relationship_editor.py`, `import_dialog.py`, `schema_widgets.py` | Editors/dialogs used by Component Editor workflows |
| Dialogs | `dialogs/project_wizard.py`, `dialogs/query_dialog.py`, `dialogs/schema_field_dialog.py` | Project creation, search/query, schema editing |
| Widgets | `widgets/landing_page.py`, `widgets/project_dashboard.py`, `widgets/schema_builder.py`, `widgets/stats_panel.py`, `widgets/treeview_sorter.py` | Landing/Dashboard use ttk (sv-ttk themed); `treeview_sorter.py` adds reusable column sorting with header indicators |
| Windows | `windows/db_explorer.py`, `windows/file_browser.py`, `windows/project_manager.py` | DB Explorer has sortable columns (including numeric strength sort) and themed controls |

### Agents (`agents/`)

| File | Purpose | Status | Usage |
|------|---------|--------|-------|
| `manager.py` | Harvester orchestrator | ✅ Active | Coordinates Scout, Analyst, Validator, Reviewer agents (CLI + GUI) |
| `scout.py` | Entity discovery agent | ✅ Active | Used by manager |
| `analyst.py` | Data mining agent | ✅ Active | Used by manager |
| `validator.py` | Validation agent | ✅ Active | Used by manager |
| `forge.py` | Review agent | ✅ Active | Used by manager |
| `models.py` | Agent data models | ✅ Active | Shared models |

### Documentation (`docs/`)

| Directory/File | Purpose |
|---------------|---------|
| `forge_user_guide.md` | Comprehensive user + developer guide |
| `harvester_agents.md` | Harvester agent details |
| `project_structure.md` | This reference |
| `notes.md` | Development notes |
| `dev_plans/` | Planning docs (current + completed phases) |
| `dev_plans/tkinter_dev/` | Tkinter development guides |
| `feature_implementations/` | Implementation reports (ConfigManager, Dark Theme, Column Sorting, etc.) |

---

## File Usage Summary

- **Actively used:** All files in `app/`, `agents/`, `converters/`, `ui/`, `config_manager.py`, `cli.py`, `extractor.py`, `storage.py`, `prompts.py`, `user_config.py`, `forge.py`
- **Theme & UX:** `app/main_app.py` applies sv-ttk dark/light theme based on user config; `ui/widgets/treeview_sorter.py` enables sortable columns in Component Editor and DB Explorer
- **Converter setup:** `converters/__init__.py` now centralizes converter registration via `create_registry()`

---

## Key Changes (Refactoring Recommendations 1–3, 5)

1. **Manager-based UI architecture:** Monolithic `forge.py` UI split into `app/main_app.py` (coordinator), `state_manager.py`, `menu_manager.py`, `project_manager.py`, and `data_manager.py` while keeping `forge.py` as a thin wrapper.
2. **Centralized configuration:** `config_manager.py` provides a singleton for loading/saving `UserConfig` (theme preference, recents, geometry).
3. **Centralized converters:** `create_registry()` in `converters/__init__.py` registers all converters once; dialogs consume the registry.
4. **Dark theme support:** sv-ttk applied at startup with light/dark preference stored in user config; UI widgets updated to ttk to respect theming.
5. **Column sorting:** Reusable `TreeviewSorter` adds click-to-sort headers (with ↑/↓ indicators) to entities/relationships views and DB Explorer, including numeric sorting for relationship strength.

