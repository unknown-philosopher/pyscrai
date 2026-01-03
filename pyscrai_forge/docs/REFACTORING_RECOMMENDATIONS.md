# PyScrAI|Forge Refactoring Recommendations

This document outlines recommended refactoring and optimization opportunities for the PyScrAI|Forge codebase, with a focus on `forge.py` and overall project improvements.

---

## 1. Critical: `forge.py` Refactoring

### Current State
- **File Size**: 1,260 lines
- **Methods**: 45+ methods in a single class
- **Responsibilities**: UI controller, state management, project management, data operations, validation, menu handling, dialogs

### Problem
`forge.py` has evolved from a simple review tool into the main application controller. With more features planned, this file will become increasingly difficult to maintain.

### Recommended Refactoring Strategy

Split `ReviewerApp` into focused, single-responsibility classes:

#### Proposed Structure

```
src/
├── app/
│   ├── __init__.py
│   ├── main_app.py          # ReviewerApp (slimmed down, ~200 lines)
│   ├── state_manager.py     # AppState management & transitions
│   ├── menu_builder.py      # Menu construction & state updates
│   ├── project_manager.py   # Project loading/saving operations
│   └── data_manager.py      # Entity/relationship data operations
```

#### 1.1 Extract State Management (`state_manager.py`)

**Extract:**
- `_transition_to_state()`
- `_build_landing_page()`
- `_build_dashboard()`
- `_build_component_editor()`
- `_update_status_bar()`
- `_update_window_title()`

**New Class:**
```python
class AppStateManager:
    """Manages UI state transitions and state-specific UI building."""
    def __init__(self, root, main_container, ...):
        self.current_state = AppState.LANDING
        ...
    
    def transition_to(self, new_state: AppState):
        """Transition to a new UI state."""
        ...
    
    def build_state_ui(self, state: AppState):
        """Build UI for a specific state."""
        ...
```

#### 1.2 Extract Menu Management (`menu_builder.py`)

**Extract:**
- `_build_ui()` (menu portion)
- `_update_menu_states()`
- `_update_recent_projects_menu()`

**New Class:**
```python
class MenuBuilder:
    """Builds and manages application menu bar."""
    def __init__(self, root, app_callbacks):
        self.root = root
        self.callbacks = app_callbacks
    
    def build_menubar(self) -> tk.Menu:
        """Build the complete menu bar."""
        ...
    
    def update_states(self, has_project: bool):
        """Update menu item enabled/disabled states."""
        ...
```

#### 1.3 Extract Project Operations (`project_manager.py`)

**Extract:**
- `_load_project()`
- `_open_project_dialog()`
- `_open_recent_project()`
- `_close_project()`
- `_new_project_wizard()`
- `_load_manifest()`
- `_open_project_manager()`
- `_open_file_browser()`

**New Class:**
```python
class ProjectController:
    """Handles project loading, saving, and management."""
    def __init__(self, user_config: UserConfig):
        self.user_config = user_config
        self.current_project: Path | None = None
        self.manifest: ProjectManifest | None = None
    
    def load_project(self, project_path: Path) -> bool:
        """Load a project and return success status."""
        ...
    
    def close_project(self):
        """Close the current project."""
        ...
```

#### 1.4 Extract Data Operations (`data_manager.py`)

**Extract:**
- `_load_packet()`
- `_load_data_file()`
- `_add_entity()`
- `_delete_selected_entity()`
- `_edit_entity()`
- `_add_relationship()`
- `_delete_selected_relationship()`
- `_edit_relationship()`
- `_refresh_ui_from_data()`
- `_update_validation_status()`
- `_commit_to_db()`
- `_export_project_data()`

**New Class:**
```python
class DataManager:
    """Manages entity and relationship data operations."""
    def __init__(self, db_path: Path | None):
        self.entities: list[Entity] = []
        self.relationships: list[Relationship] = []
        self.validation_report: dict = {}
        self.db_path = db_path
    
    def load_from_packet(self, packet_path: Path):
        """Load entities/relationships from a review packet."""
        ...
    
    def commit_to_database(self):
        """Commit current data to database."""
        ...
```

#### 1.5 Slimmed-Down `ReviewerApp` (`main_app.py`)

**Remaining Responsibilities:**
- Application initialization
- Coordinating between managers
- High-level event handling
- Window lifecycle

**Structure:**
```python
class ReviewerApp:
    """Main application controller (coordinator)."""
    
    def __init__(self, packet_path: Path | None = None, project_path: Path | None = None):
        self.root = tk.Tk()
        self.user_config = UserConfig.load()
        
        # Initialize managers
        self.project_controller = ProjectController(self.user_config)
        self.data_manager = DataManager(None)
        self.state_manager = AppStateManager(self.root, ...)
        self.menu_builder = MenuBuilder(self.root, self._get_callbacks())
        
        # Build UI
        self._initialize_ui()
        
        # Load initial state
        if project_path:
            self.project_controller.load_project(project_path)
            self.state_manager.transition_to(AppState.DASHBOARD)
        else:
            self.state_manager.transition_to(AppState.LANDING)
    
    def _get_callbacks(self) -> dict:
        """Return callbacks for menu/dialog actions."""
        return {
            'new_project': self._on_new_project,
            'open_project': self._on_open_project,
            ...
        }
```

### Benefits of Refactoring

1. **Maintainability**: Each class has a single, clear responsibility
2. **Testability**: Smaller classes are easier to unit test
3. **Readability**: Related functionality is grouped together
4. **Extensibility**: New features can be added to specific managers without touching others
5. **Reduced Cognitive Load**: Developers can focus on one area at a time

### Migration Strategy

1. **Phase 1**: Create new manager classes alongside existing code
2. **Phase 2**: Gradually move methods to managers, keeping `ReviewerApp` as a facade
3. **Phase 3**: Update all internal references to use managers
4. **Phase 4**: Remove old methods from `ReviewerApp`

---

## 2. Remove Unused Code

### 2.1 `reviewer_cli.py`

**Status**: ⚠️ **UNUSED**

**Recommendation**: **DELETE** this file. It's redundant with `cli.py`'s `forge gui` command.

**Action:**
```bash
# Remove file
rm pyscrai_forge/src/reviewer_cli.py
```

### 2.2 `EditDialog` Class in `forge.py`

**Status**: ⚠️ **POTENTIALLY UNUSED**

**Recommendation**: Check if `EditDialog` (lines 1217-1254) is actually used. If not, remove it. If it is, move it to `ui/dialogs/edit_dialog.py`.

---

## 3. Converter Registration Centralization

### Current Issue
Converters are registered in `ui/import_dialog.py`, which creates tight coupling.

### Recommendation
Create a centralized converter initialization:

**New File**: `src/converters/__init__.py`
```python
from .registry import FormatRegistry
from .pdf_converter import PDFConverter
from .html_converter import HTMLConverter
from .docx_converter import DOCXConverter
from .ocr_converter import OCRConverter

def create_registry() -> FormatRegistry:
    """Create and configure the converter registry."""
    registry = FormatRegistry()
    registry.register('.pdf', PDFConverter)
    registry.register('.html', HTMLConverter)
    registry.register('.htm', HTMLConverter)
    registry.register('.docx', DOCXConverter)
    registry.register('.png', OCRConverter)
    registry.register('.jpg', OCRConverter)
    registry.register('.jpeg', OCRConverter)
    return registry

__all__ = ['FormatRegistry', 'create_registry']
```

**Update**: `ui/import_dialog.py` to use `create_registry()` instead of manual registration.

---

## 4. Error Handling Improvements

### Current State
Many methods use bare `except:` clauses or print errors to console.

### Recommendations

1. **Use Proper Logging**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   
   # Instead of: print(f"Failed to load: {e}")
   logger.error(f"Failed to load user config: {e}", exc_info=True)
   ```

2. **User-Friendly Error Messages**
   - Replace `messagebox.showerror("Error", str(e))` with formatted messages
   - Add error codes for common issues
   - Provide recovery suggestions

3. **Error Recovery**
   - Add retry logic for network operations
   - Graceful degradation when optional features fail

---

## 5. Configuration Management

### Current State
`UserConfig` is loaded/saved manually in multiple places.

### Recommendation
Create a singleton configuration manager:

```python
# src/config_manager.py
class ConfigManager:
    _instance = None
    _config: UserConfig | None = None
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_config(self) -> UserConfig:
        if self._config is None:
            self._config = UserConfig.load()
        return self._config
    
    def save_config(self):
        if self._config:
            self._config.save()
```

---

## 6. Type Hints & Documentation

### Current State
Some methods lack type hints or docstrings.

### Recommendation
1. Add type hints to all public methods
2. Use `TYPE_CHECKING` for forward references
3. Add docstrings following Google/NumPy style
4. Consider using `mypy` for type checking

---

## 7. Testing Infrastructure

### Current State
No tests implemented (as noted in README).

### Recommendations

1. **Unit Tests**
   - Test each manager class independently
   - Mock dependencies (database, file system, LLM providers)

2. **Integration Tests**
   - Test state transitions
   - Test project loading/saving workflows

3. **UI Tests**
   - Consider using `pytest-tkinter` or similar
   - Test critical user workflows

**Suggested Structure:**
```
tests/
├── unit/
│   ├── test_project_manager.py
│   ├── test_data_manager.py
│   └── test_state_manager.py
├── integration/
│   └── test_app_workflows.py
└── fixtures/
    └── sample_data.py
```

---

## 8. Performance Optimizations

### 8.1 Database Operations

**Current**: Individual saves in `commit_extraction_result()`
**Recommendation**: Use batch transactions

```python
def commit_extraction_result(db_path: Path, entities: list[Entity], relationships: list[Relationship]):
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            # Batch insert entities
            cursor.executemany("INSERT OR REPLACE INTO entities ...", entity_data)
            # Batch insert relationships
            cursor.executemany("INSERT OR REPLACE INTO relationships ...", rel_data)
    finally:
        conn.close()
```

### 8.2 UI Updates

**Current**: Full treeview refresh on every change
**Recommendation**: Incremental updates

```python
def _update_entity_in_tree(self, entity: Entity):
    """Update a single entity in the treeview without full refresh."""
    item = self.entities_tree.item(entity.id)
    self.entities_tree.item(entity.id, values=(...))
```

### 8.3 Lazy Loading

**Recommendation**: Load project data on-demand rather than all at once.

---

## 9. Code Quality Improvements

### 9.1 Constants

Extract magic strings/numbers to constants:

```python
# src/constants.py
class AppConstants:
    DEFAULT_WINDOW_SIZE = "1400x900"
    MAX_RECENT_PROJECTS = 10
    VALIDATION_COLORS = {
        'error': '#ffcccc',
        'warning': '#fff4cc',
        'success': '#ccffcc'
    }
```

### 9.2 Enums

Use enums for state values:

```python
# Already done for AppState, but consider:
class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"
```

### 9.3 Path Handling

Use `pathlib.Path` consistently (already mostly done, but verify all file operations).

---

## 10. Documentation Improvements

### Recommendations

1. **API Documentation**
   - Add docstrings to all public methods
   - Document parameters and return types
   - Add usage examples

2. **Architecture Diagrams**
   - Create diagrams showing class relationships
   - Document data flow through the application

3. **Developer Onboarding**
   - Add a "Contributing" guide
   - Document the refactoring plan
   - Add code style guidelines

---

## 11. Dependency Management

### Current State
All dependencies in `setup.py` are required.

### Recommendation
Use `extras_require` for optional features:

```python
setup(
    ...
    install_requires=[
        "pydantic>=2.0.0",
        "httpx>=0.25.0",
        # ... core deps
    ],
    extras_require={
        "ocr": ["pytesseract>=0.3.10", "Pillow>=8.0.0"],
        "dev": ["pytest>=7.0.0", "pytest-asyncio>=0.21.0", "mypy>=1.0.0"],
        "all": ["pytesseract>=0.3.10", "Pillow>=8.0.0", "pytest>=7.0.0", ...]
    }
)
```

---

## 12. Quality of Life Improvements

### 12.1 Keyboard Shortcuts

Add keyboard shortcuts for common actions:
- `Ctrl+N` - New Project
- `Ctrl+O` - Open Project
- `Ctrl+S` - Save/Commit
- `Ctrl+E` - Export
- `F5` - Refresh

### 12.2 Recent Files

Extend recent projects to include recently opened files/packets.

### 12.3 Auto-save

Implement auto-save for unsaved changes (with user preference toggle).

### 12.4 Undo/Redo

Consider adding undo/redo functionality for entity/relationship edits.

### 12.5 Search/Filter

Add search/filter capabilities to entity and relationship treeviews.

### 12.6 Progress Indicators

Improve progress indicators for long-running operations (import, extraction).

### 12.7 Theme Support

Implement theme support (light/dark mode) using `UserConfig.preferences.theme`.

---

## Implementation Priority

### High Priority (Before 1.0)
1. ✅ Refactor `forge.py` (critical for maintainability)
2. ✅ Remove `reviewer_cli.py`
3. ✅ Centralize converter registration
4. ✅ Improve error handling

### Medium Priority (1.0+)
5. Configuration manager singleton
6. Batch database operations
7. Add unit tests
8. Type hints & documentation

### Low Priority (Future)
9. Performance optimizations
10. Keyboard shortcuts
11. Undo/redo
12. Theme support

---

## Conclusion

The primary focus should be on refactoring `forge.py` to improve maintainability and prepare for future features. The proposed structure will make the codebase more modular, testable, and easier to extend.

Start with the state management and project management extractions, as these are the most self-contained and will provide immediate benefits.

