# UI Window Size Reference

This document lists all window geometry settings in the PyScrAI|Forge UI for easy reference and potential consolidation.

## Main Application Windows

### ReviewerApp (Main Window)
- **File**: `pyscrai_forge/harvester/forge.py`
- **Line**: 69
- **Size**: `"1400x900"`

## Dialog Windows

### Project Wizard Dialog
- **File**: `pyscrai_forge/harvester/ui/dialogs/project_wizard.py`
- **Line**: 26
- **Size**: `"700x600"`

### Query Dialog
- **File**: `pyscrai_forge/harvester/ui/dialogs/query_dialog.py`
- **Line**: 24
- **Size**: `"800x600"`

### Schema Field Dialog
- **File**: `pyscrai_forge/harvester/ui/dialogs/schema_field_dialog.py`
- **Line**: 25
- **Size**: `"500x400"`

### Import Dialog
- **File**: `pyscrai_forge/harvester/ui/dialogs/import_dialog.py`
- **Line**: 11
- **Size**: `"800x600"`

## Window Classes

### Project Manager Window
- **File**: `pyscrai_forge/harvester/ui/windows/project_manager.py`
- **Line**: 27
- **Size**: `"900x700"`

### Database Explorer Window
- **File**: `pyscrai_forge/harvester/ui/windows/db_explorer.py`
- **Line**: 29
- **Size**: `"1200x800"`

### File Browser Window (Deprecated - to be removed)
- **File**: `pyscrai_forge/harvester/ui/windows/file_browser.py`
- **Line**: 24
- **Size**: `"900x600"`

## Editor Windows

### Tabbed Entity Editor
- **File**: `pyscrai_forge/harvester/ui/entity_editor.py`
- **Line**: 11
- **Size**: `"600x700"`

### Relationship Editor
- **File**: `pyscrai_forge/harvester/ui/relationship_editor.py`
- **Line**: 11
- **Size**: `"500x600"`

## Widget Dialogs

### Schema Builder Dialog
- **File**: `pyscrai_forge/harvester/ui/widgets/schema_builder.py`
- **Line**: 100
- **Size**: `"400x150"`

### Dependency Manager Dialog
- **File**: `pyscrai_forge/harvester/ui/widgets/dependency_manager.py`
- **Line**: 88
- **Size**: `"400x200"`

### File Browser New Folder Dialog
- **File**: `pyscrai_forge/harvester/ui/windows/file_browser.py`
- **Line**: 260
- **Size**: `"400x120"`

## Notes

- All sizes are in format `"WIDTHxHEIGHT"` (string format for Tkinter geometry)
- Some dialogs use dynamic positioning (e.g., `f"+{x}+{y}"`) for centering
- Consider creating a centralized configuration file for window sizes if refactoring

## Potential Consolidation

If consolidating window sizes, consider creating a configuration module:

```python
# ui/config.py
WINDOW_SIZES = {
    "main": "1400x900",
    "project_wizard": "700x600",
    "project_manager": "900x700",
    "db_explorer": "1200x800",
    "entity_editor": "600x700",
    "relationship_editor": "500x600",
    "import_dialog": "800x600",
    "query_dialog": "800x600",
    "schema_field": "500x400",
    "schema_builder": "400x150",
    "dependency_manager": "400x200",
}
```

Then import and use: `self.geometry(WINDOW_SIZES["main"])`

