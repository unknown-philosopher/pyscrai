# Deprecated Files for PyScrAI 2.0

This document lists files that are no longer needed in PyScrAI 2.0 and should be marked with `_dep_` prefix when creating the 2.0 branch.

## Confirmed Deprecated Files

Already Deleted~
<!-- ### UI Widgets
- **`pyscrai_forge/src/ui/widgets/narrative_panel.py`**
  - **Reason**: Replaced by Chronicle phase UI (`pyscrai_forge/phases/chronicle/ui.py`)
  - **Status**: Narrative tab was removed from dashboard; Chronicle phase handles narrative generation
  - **References**: No active imports found -->

### Legacy Entry Points
- **`pyscrai_forge/src/forge.py`**
  - **Reason**: Legacy entry point that references old `COMPONENT_EDITOR` state
  - **Status**: Superseded by `main_app.py`; still imported by `cli.py` for "gui" command but should be updated
  - **Action**: Update `cli.py` to import directly from `main_app.py` instead

## Potentially Deprecated (Needs Review)

### Legacy State Management
- **`pyscrai_forge/src/app/state_manager.py`** - `_build_component_editor()` method
  - **Reason**: Replaced by `FoundryPanel` in Phase 1 (Foundry)
  - **Status**: Still exists as fallback/compatibility code
  - **Action**: Consider removing after ensuring all references use FoundryPanel

## Files Still in Use (NOT Deprecated)

These files are still actively used and should NOT be deprecated:

- `entity_editor.py` - Used by `data_manager.py` and `db_explorer.py`
- `relationship_editor.py` - Used by `data_manager.py` and `db_explorer.py`
- `schema_widgets.py` - Used by `entity_editor.py`
- `schema_builder.py` - Used by `project_manager.py` and `project_wizard.py`
- `schema_field_dialog.py` - Used by `schema_builder.py`
- `stats_panel.py` - Used by `db_explorer.py`
- `dependency_manager.py` - Used by `project_manager.py`
- `query_dialog.py` - Used by `db_explorer.py`
- `operation_handlers.py` - Used by `chat_dialog.py` and `user_proxy.py`
- `extractor.py` - Used for file extraction workflows

## Migration Notes

When renaming files with `_dep_` prefix:

1. **Update imports**: ✅ COMPLETED - All imports updated
2. **Update CLI**: ✅ COMPLETED - Updated `cli.py` line 46 to import from `main_app.py` instead of `forge.py`
3. **Update `__init__.py`**: ✅ COMPLETED - Updated `pyscrai_forge/src/__init__.py` to import from `main_app.py`
4. **Test**: Ensure all entry points still work after deprecation

## Recommended Renaming Commands

```bash
# Rename deprecated files
mv pyscrai_forge/src/ui/widgets/narrative_panel.py pyscrai_forge/src/ui/widgets/_dep_narrative_panel.py
mv pyscrai_forge/src/forge.py pyscrai_forge/src/_dep_forge.py

# Update imports in cli.py
# Change: from pyscrai_forge.src.forge import main as reviewer_main
# To: from pyscrai_forge.src.app.main_app import ReviewerApp
```

