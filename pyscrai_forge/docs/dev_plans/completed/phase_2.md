---
name: Phase 2 Implementation
overview: Implement Project Management Interface, Database Explorer, and Project Directory Viewer for the Harvester UI. This enables full project configuration management, database browsing, and file structure visualization without leaving the UI.
todos:
  - id: project-manager-window
    content: Create project_manager.py main window with tabbed interface for editing ProjectManifest fields (Basic Info, Schema, LLM Settings, Systems, Dependencies, Advanced)
    status: pending
  - id: schema-builder-widget
    content: Create schema_builder.py reusable widget for editing entity_schemas dict with grid view (entity types, fields, types, required flags)
    status: pending
  - id: schema-field-dialog
    content: Create schema_field_dialog.py modal for adding/editing individual schema fields
    status: pending
  - id: project-wizard
    content: Create project_wizard.py multi-step wizard for creating new projects (Identity, Schemas, LLM, Review)
    status: pending
    dependencies:
      - schema-builder-widget
  - id: db-explorer-window
    content: Create db_explorer.py main window with entity browser, relationship browser, statistics panel, and query builder
    status: pending
  - id: stats-panel-widget
    content: Create stats_panel.py reusable widget for displaying database statistics (entity counts, relationship counts)
    status: pending
  - id: query-dialog
    content: Create query_dialog.py for SQL query input and results display
    status: pending
  - id: file-browser-window
    content: Create file_browser.py window with directory tree view and file preview panel
    status: pending
  - id: reviewer-integration
    content: Integrate all new windows into ReviewerApp menubar (Project menu, Database menu) with appropriate handlers
    status: pending
    dependencies:
      - project-manager-window
      - db-explorer-window
      - file-browser-window
      - project-wizard
  - id: dependency-manager-widget
    content: Create dependency_manager.py widget for editing mod dependencies key-value pairs
    status: pending
---

# Phase 2: Project Management Interface - Implementation Plan

## Overview

Phase 2 adds three major UI components to the Harvester:

1. **Project Configuration Manager** - Full project.json editing interface
2. **Database Explorer** - Browse and manage world.db contents
3. **Project Directory Structure Viewer** - Visual file browser

These components integrate with the existing Reviewer UI and leverage the existing `ProjectController`, `ProjectManifest`, and database storage layer.

## Architecture

```javascript
pyscrai_forge/harvester/
├── ui/
│   ├── windows/                    # NEW - Main window classes
│   │   ├── __init__.py
│   │   ├── project_manager.py      # Project configuration UI
│   │   ├── db_explorer.py          # Database browser window
│   │   └── file_browser.py         # Directory structure viewer
│   ├── dialogs/                    # NEW - Dialog windows
│   │   ├── __init__.py
│   │   ├── project_wizard.py       # Create new project wizard
│   │   ├── schema_field_dialog.py  # Add/edit entity schema field
│   │   └── query_dialog.py         # SQL query input dialog
│   └── widgets/                    # NEW - Reusable widgets
│       ├── __init__.py
│       ├── schema_builder.py       # Entity schema grid editor
│       ├── dependency_manager.py   # Dependency key-value editor
│       └── stats_panel.py          # Database statistics display
```



## Implementation Tasks

### 2.1 Project Configuration Manager

**File: `pyscrai_forge/harvester/ui/windows/project_manager.py`**Create a tabbed window for editing `ProjectManifest` with the following tabs:

- **Basic Info Tab**: Name, description, author, version (Entry widgets)
- **Schema Tab**: Entity schema builder (reuse `SchemaBuilderWidget`)
- **LLM Settings Tab**: Provider dropdown, default model, fallback model
- **Systems Tab**: Checkboxes for enabled_systems (events, memory, relationships)
- **Dependencies Tab**: Key-value editor for mod dependencies
- **Advanced Tab**: Custom settings (JSON text area), simulation settings

**Integration points:**

- Use `ProjectController` to load/save manifests
- Validate with `ProjectManifest` Pydantic model
- Integrate into ReviewerApp menubar: "Project" → "Manage Project..."

**Key methods:**

- `load_project(project_path: Path)` - Load existing project
- `save_manifest()` - Write to project.json via ProjectController
- `validate_and_save()` - Pydantic validation before save

**File: `pyscrai_forge/harvester/ui/dialogs/project_wizard.py`**Multi-step wizard for creating new projects:

1. **Step 1: Project Identity** - Name, author, description
2. **Step 2: Entity Schemas** - Initial entity types and fields
3. **Step 3: LLM Configuration** - Provider and model selection
4. **Step 4: Review & Create** - Show summary, create project bundle

**Implementation:**

- Use `ttk.Notebook` or custom step navigation
- Call `ProjectController.create_project()` on finish
- Initialize database via `_init_database()`

**File: `pyscrai_forge/harvester/ui/widgets/schema_builder.py`**Grid-based editor for `entity_schemas` dict:

- Treeview showing: Entity Type → Field Name → Field Type → Required?
- Buttons: "Add Entity Type", "Add Field", "Edit Field", "Delete"
- Field type dropdown: string, integer, float, boolean, select, list
- Validation: No duplicate field names per entity type

**Integration:**

- Reused by Project Manager Schema tab and Project Wizard Step 2

**File: `pyscrai_forge/harvester/ui/dialogs/schema_field_dialog.py`**Modal dialog for adding/editing a schema field:

- Field name (Entry)
- Field type (Combobox: string, integer, float, boolean, select, list)
- Required checkbox
- Options field (for select/list types)
- Validation before OK

### 2.2 Database Explorer

**File: `pyscrai_forge/harvester/ui/windows/db_explorer.py`**Main window with three panels:

- **Left sidebar**: Database selector, navigation tree (Entities/Relationships/Queries)
- **Center**: Table browser (Treeview with filtering)
- **Right**: Statistics panel, query builder

**Entity Browser:**

- Treeview columns: ID, Type, Name, Created, Updated
- Filter by type, name (search), validation status
- Double-click to open entity in `TabbedEntityEditor`
- Context menu: Edit, Delete, Export to JSON

**Relationship Browser:**

- Treeview columns: ID, Source, Target, Type, Strength
- Filter by type, source, target
- Double-click to open in `RelationshipEditor`
- Show ghost nodes (relationships pointing to non-existent entities)

**Statistics Panel:**

- Entity count by type (simple label counters)
- Relationship type distribution
- Total counts
- Refresh button

**Database Connection:**

- Recent databases dropdown (store in user config)
- Browse button for file picker
- Connection status indicator (green/red)
- Load project's world.db automatically if project loaded

**Query Builder:**

- Simple SQL input (Text widget)
- Execute button
- Results table
- Export results button

**File: `pyscrai_forge/harvester/ui/widgets/stats_panel.py`**Reusable statistics display widget:

- Entity type pie chart (simple text summary for now, chart deferred to Phase 4)
- Relationship type counts
- Quick stats (total entities, relationships, orphan count)

**Integration:**

- Use existing `storage.py` functions: `load_all_entities()`, `load_all_relationships()`
- Add menubar item in ReviewerApp: "Database" → "Explore Database..."
- Integrate with project path: Auto-load if project is set

**Database Operations:**

- Add `delete_entity()` and `delete_relationship()` calls (already in storage.py)
- Batch delete with confirmation dialog
- Export selected entities to JSON file

### 2.3 Project Directory Structure Viewer

**File: `pyscrai_forge/harvester/ui/windows/file_browser.py`**Split-pane window:

- **Left**: Directory tree (`ttk.Treeview` with folder icons)
- **Right**: File preview panel

**Directory Tree:**

- Lazy loading (expand on demand)
- Show file sizes and modification dates
- Icons for file types (.json, .db, .txt, etc.)
- Root: Project directory from `ProjectController.project_path`

**File Preview:**

- Text files: Syntax-highlighted preview (plain Text widget initially)
- JSON files: Prettified JSON display
- Images: Thumbnail preview (if in assets/images)
- Binary files: "Binary file" message

**Quick Actions Toolbar:**

- Create Folder button
- Upload File button (copy to project/assets)
- Open in Explorer button (OS file manager)
- Delete button (with confirmation)
- Refresh button

**Context Menu:**

- Open file location
- Delete file
- Copy path to clipboard

**Integration:**

- Menubar: "Project" → "Browse Files..."
- Only available if project is loaded
- Sync with ProjectController to show correct structure

## UI Integration

**Modify: `pyscrai_forge/harvester/reviewer.py`**Add new menu items to ReviewerApp:

```python
project_menu = tk.Menu(menubar, tearoff=0)
project_menu.add_command(label="Manage Project...", command=self._open_project_manager)
project_menu.add_command(label="Browse Files...", command=self._open_file_browser)
project_menu.add_command(label="New Project...", command=self._new_project_wizard)
menubar.add_cascade(label="Project", menu=project_menu)

db_menu = tk.Menu(menubar, tearoff=0)
db_menu.add_command(label="Explore Database...", command=self._open_db_explorer)
menubar.add_cascade(label="Database", menu=db_menu)
```



## Data Flow

### Project Manager Flow

```javascript
User opens Project Manager
  → Load project.json via ProjectController
  → Parse ProjectManifest (Pydantic)
  → Populate UI tabs
  → User edits fields
  → Validate on Save
  → Write via ProjectController.save_manifest()
```



### Database Explorer Flow

```javascript
User opens Database Explorer
  → Select database path (or auto-load from project)
  → Load all entities via storage.load_all_entities()
  → Load all relationships via storage.load_all_relationships()
  → Populate Treeviews
  → User filters/browses
  → Double-click opens in existing editor dialogs
```



### File Browser Flow

```javascript
User opens File Browser
  → Get project_path from ReviewerApp or ProjectController
  → Build directory tree (lazy load)
  → User clicks file
  → Load file content
  → Display in preview panel
```



## Dependencies

- Existing: `ProjectController`, `ProjectManifest`, `storage.py`, `TabbedEntityEditor`, `RelationshipEditor`
- New: None (all Tkinter standard library)
- Future (Phase 4): Charting libraries for statistics visualization

## Validation & Error Handling

- **Project Manager**: Validate ProjectManifest with Pydantic before save, show error dialog on validation failure
- **Database Explorer**: Handle missing database files, invalid SQL queries, foreign key violations on delete
- **File Browser**: Handle permission errors, large files (limit preview size), binary file detection

## Testing Considerations

- Test Project Manager with existing projects (load/edit/save cycle)
- Test Project Wizard creates valid project structure
- Test Database Explorer with empty and populated databases
- Test File Browser with various file types and sizes
- Integration: Ensure all windows work together (e.g., edit project → reload database explorer)

## Performance Considerations

- Database Explorer: Lazy load entity/relationship lists for large databases (>1000 entities)
- File Browser: Limit preview size to 1MB for text files
- Schema Builder: Validate incrementally as user types
- All windows: Use `update_idletasks()` for long operations to keep UI responsive


## Newly Implemented Features (2026)

### 1. Automatic Entity/Relationship Backup
- After each import, extracted entities and relationships are automatically saved as a timestamped JSON file in the project's `/data` directory.
- This provides a backup and audit trail for all imported data, even before committing to the database.

### 2. Database Reset Button
- The Database Explorer now features a red "Reset DB" button in the toolbar.
- Clicking this button prompts for confirmation and, if confirmed, wipes all entities and relationships from the current `world.db`.
- This is useful for quickly clearing a project database during testing or iteration.

### 3. Robust Database Auto-Connect
- When a project is loaded in the Reviewer, opening the Database Explorer will automatically connect to the project's `world.db`.
- No manual selection is required if a project is active.

### 4. Improved Error Handling in Database Explorer
- The Database Explorer now guards against UI errors if widgets are not yet initialized, preventing crashes if the database is loaded before the UI is ready.
- All widget attributes are pre-initialized and checked before use.

### 5. UI/UX Polish
- Confirmation dialogs and status messages have been added for destructive actions (e.g., database reset, entity/relationship deletion).
- The UI now provides clear feedback after major actions (import, commit, reset).