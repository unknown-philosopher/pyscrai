# Tkinter UI Guide (Harvester/forge)

Practical rules distilled from recent fixes to avoid recurring UI/data bugs.

## Enum and Case Handling
- Always pass enum **values** (lowercase) to/from widgets; normalize on change (e.g., `val.lower()`).
- Mirror the enum source of truth in `pyscrai_core.models` (e.g., `EntityType`, `RelationshipType`, `RelationshipVisibility`).
- When showing friendly labels, convert back to enum values before validation.

## Data Shape Alignment
- Use the exact keys produced by `model_dump_json()` (lowercase component keys: `descriptor`, `cognitive`, `spatial`, `state`).
- `StateComponent.resources_json` is a **string**; parse on load, stringify on save.
- `Relationship` fields are `source_id`, `target_id`, `relationship_type`, `visibility`; do not invent `source`/`target`/`type` keys.

## Dialog Patterns (Toplevel)
- Add `transient`, `grab_set`, and a bottom button row with **Save** and **Cancel**.
- For `Text` widgets, bind `<FocusOut>` to persist edits (e.g., bio, description, metadata).
- Rebuild dependent tabs (e.g., State schema) when driving fields change (entity type) to keep UI in sync.

## Combobox Patterns
- Populate with enum-friendly values (lowercase). Normalize selection to lowercase before storing.
- For entity pickers, display names but store IDs; keep `id -> name` and `name -> id` maps.
- Allow typing for quick search (`state="readonly"` only when you need strict options).

## Treeview Display
- Show human-friendly names, but keep IDs in data; build lookups on refresh.
- Tag rows for validation status (warning/error) and refresh after any mutation.

## Validation and Save
- After add/edit/delete, refresh UI and call validation update; block commit on critical errors.
- Validate through Pydantic before persisting; surface error messages to the user.
- When saving JSON blobs (metadata/resources), validate JSON but store the original string.

## Testing Checklist (manual quick pass)
- Entity: edit all tabs; change type, bio, tags; save; re-open to confirm persistence.
- State: edit resources; save; re-open; confirm stringified storage survives reload.
- Relationship: source/target dropdowns show names, save stores IDs; type/visibility accept enum values; metadata saves.
- Validation banner updates after add/delete/edit; commit is blocked if critical errors exist.

Keep UIs thin: transform UI selections into model-shaped data, then let Pydantic validate. When in doubt, inspect `model_dump_json()` to confirm expected shapes and keys.
