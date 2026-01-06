"""Data management for PyScrAI|Forge application.

Handles entity and relationship data operations, loading, saving, and UI updates.
"""

from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime, UTC
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship, ProjectManifest
    from tkinter import Tk


class DataManager:
    """Manages entity and relationship data operations."""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        on_data_changed: Optional[Callable[[], None]] = None,
    ):
        """Initialize data manager.
        
        Args:
            db_path: Path to database file
            on_data_changed: Callback when data changes
        """
        self.db_path = db_path
        self.on_data_changed = on_data_changed
        
        self.entities: list["Entity"] = []
        self.relationships: list["Relationship"] = []
        self.validation_report: dict = {}
        
        # UI references (set by main app)
        self.entities_tree: Optional[ttk.Treeview] = None
        self.relationships_tree: Optional[ttk.Treeview] = None
        self.validation_frame: Optional[ttk.Frame] = None
        self.validation_label: Optional[ttk.Label] = None
        self.project_path: Optional[Path] = None
        self.manifest: Optional["ProjectManifest"] = None
        self.root: Optional["Tk"] = None
        
        # Sorters (set by state manager)
        self.entities_sorter: Optional[any] = None
        self.relationships_sorter: Optional[any] = None
    
    def set_ui_references(
        self,
        entities_tree: ttk.Treeview,
        relationships_tree: ttk.Treeview,
        validation_frame: Optional[ttk.Frame] = None,
        validation_label: Optional[ttk.Label] = None,
        root: Optional["Tk"] = None,
        project_path: Optional[Path] = None,
        manifest: Optional["ProjectManifest"] = None,
        entities_sorter: Optional[any] = None,
        relationships_sorter: Optional[any] = None,
    ):
        """Set UI component references.
        
        Args:
            entities_tree: Entities treeview
            relationships_tree: Relationships treeview
            validation_frame: Validation frame (optional)
            validation_label: Validation label (optional)
            root: Root window (optional)
            project_path: Project path (optional)
            manifest: Project manifest (optional)
            entities_sorter: Entities treeview sorter (optional)
            relationships_sorter: Relationships treeview sorter (optional)
        """
        self.entities_tree = entities_tree
        self.relationships_tree = relationships_tree
        self.validation_frame = validation_frame
        self.validation_label = validation_label
        self.root = root
        self.project_path = project_path
        self.manifest = manifest
        self.entities_sorter = entities_sorter
        self.relationships_sorter = relationships_sorter
    
    def set_db_path(self, db_path: Optional[Path]) -> None:
        """Update database path.
        
        Args:
            db_path: New database path
        """
        self.db_path = db_path
    
    def load_from_packet(self, path: Path) -> bool:
        """Load entities/relationships from a review packet.
        
        Args:
            path: Path to packet file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            from pyscrai_core import Actor, Entity, Location, Polity, Relationship
            
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            
            # Reconstruct Entities using Pydantic
            self.entities = []
            raw_entities = data.get("entities", [])
            for raw in raw_entities:
                try:
                    e_type_val = "abstract"
                    if "descriptor" in raw and "entity_type" in raw["descriptor"]:
                        e_type_val = raw["descriptor"]["entity_type"]
                    
                    if e_type_val == "actor":
                        obj = Actor.model_validate(raw)
                    elif e_type_val == "polity":
                        obj = Polity.model_validate(raw)
                    elif e_type_val == "location":
                        obj = Location.model_validate(raw)
                    else:
                        obj = Entity.model_validate(raw)
                    
                    self.entities.append(obj)
                except Exception as e:
                    print(f"Failed to reconstruct entity: {e}")
            
            # Reconstruct Relationships
            self.relationships = []
            for raw in data.get("relationships", []):
                try:
                    self.relationships.append(Relationship.model_validate(raw))
                except Exception as e:
                    print(f"Failed to reconstruct relationship: {e}")
            
            self.validation_report = data.get("validation_report", {})
            
            # Note: refresh_ui() will be called by main_app after UI references are set
            # This ensures treeviews exist before we try to populate them
            if self.on_data_changed:
                self.on_data_changed()
            
            return True
            
        except Exception as e:
            if self.root:
                messagebox.showerror("Error", f"Failed to load packet: {str(e)}", parent=self.root)
            return False
    
    def load_from_file(self, parent_window) -> bool:
        """Load data from a JSON file via dialog.
        
        Args:
            parent_window: Parent window for dialog
            
        Returns:
            True if loaded successfully, False otherwise
        """
        file_path = filedialog.askopenfilename(
            title="Load Component Data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=parent_window
        )
        if file_path:
            return self.load_from_packet(Path(file_path))
        return False
    
    def add_entity(self) -> None:
        """Add a new entity."""
        from pyscrai_core import Actor, DescriptorComponent, EntityType, StateComponent
        new_ent = Actor(
            descriptor=DescriptorComponent(name="New Entity", entity_type=EntityType.ACTOR),
            state=StateComponent()
        )
        self.entities.append(new_ent)
        self.refresh_ui()
        self.update_validation_status()
        self.edit_entity(entity_id=new_ent.id)
    
    def delete_selected_entity(self) -> None:
        """Delete selected entities."""
        if not self.entities_tree:
            return
        
        selected = self.entities_tree.selection()
        if not selected:
            return
        
        # Remove
        self.entities = [e for e in self.entities if e.id not in selected]
        self.refresh_ui()
        self.update_validation_status()
        
        if self.on_data_changed:
            self.on_data_changed()
    
    def edit_entity(self, event=None, entity_id: Optional[str] = None) -> None:
        """Edit an entity.
        
        Args:
            event: Event object (optional)
            entity_id: Entity ID to edit (optional, uses selection if not provided)
        """
        if not self.entities_tree or not self.root:
            return
        
        if not entity_id:
            sel = self.entities_tree.selection()
            if not sel:
                return
            entity_id = sel[0]
        
        ent = next((e for e in self.entities if e.id == entity_id), None)
        if not ent:
            return
        
        from pyscrai_forge.src.ui.entity_editor import TabbedEntityEditor
        from pyscrai_core import Actor, Entity, Location, Polity, ProjectManifest
        
        # Convert Pydantic model to dict for editor
        ent_data = json.loads(ent.model_dump_json())
        
        # Load project manifest if available
        manifest = self.manifest
        if not manifest and self.project_path:
            try:
                manifest_path = self.project_path / "project.json"
                if manifest_path.exists():
                    with open(manifest_path, 'r') as f:
                        manifest_data = json.load(f)
                        manifest = ProjectManifest.model_validate(manifest_data)
            except Exception:
                pass
        
        def on_save(new_data):
            try:
                # Re-validate and update
                if new_data.get('descriptor', {}).get('entity_type') == 'actor':
                    updated = Actor.model_validate(new_data)
                elif new_data.get('descriptor', {}).get('entity_type') == 'polity':
                    updated = Polity.model_validate(new_data)
                elif new_data.get('descriptor', {}).get('entity_type') == 'location':
                    updated = Location.model_validate(new_data)
                else:
                    updated = Entity.model_validate(new_data)
                
                # Update in list
                idx = self.entities.index(ent)
                self.entities[idx] = updated
                self.refresh_ui()
                
                if self.on_data_changed:
                    self.on_data_changed()
            except Exception as e:
                messagebox.showerror("Validation Error", str(e), parent=self.root)
        
        TabbedEntityEditor(self.root, ent_data, project_manifest=manifest, on_save=on_save)
    
    def add_relationship(self) -> None:
        """Add a new relationship."""
        if not self.entities:
            return
        from pyscrai_core import Relationship, RelationshipType
        new_rel = Relationship(
            source_id=self.entities[0].id,
            target_id=self.entities[0].id,
            relationship_type=RelationshipType.CUSTOM
        )
        self.relationships.append(new_rel)
        self.refresh_ui()
        self.update_validation_status()
        self.edit_relationship(rel_id=new_rel.id)
    
    def delete_selected_relationship(self) -> None:
        """Delete selected relationships."""
        if not self.relationships_tree:
            return
        
        selected = self.relationships_tree.selection()
        if not selected:
            return
        
        self.relationships = [r for r in self.relationships if r.id not in selected]
        self.refresh_ui()
        self.update_validation_status()
        
        if self.on_data_changed:
            self.on_data_changed()
    
    def edit_relationship(self, event=None, rel_id: Optional[str] = None) -> None:
        """Edit a relationship.
        
        Args:
            event: Event object (optional)
            rel_id: Relationship ID to edit (optional, uses selection if not provided)
        """
        if not self.relationships_tree or not self.root:
            return
        
        if not rel_id:
            sel = self.relationships_tree.selection()
            if not sel:
                return
            rel_id = sel[0]
        
        rel = next((r for r in self.relationships if r.id == rel_id), None)
        if not rel:
            return
        
        from pyscrai_forge.src.ui.relationship_editor import RelationshipEditor
        from pyscrai_core import Relationship
        
        rel_data = json.loads(rel.model_dump_json())
        # Create entity ID to name mapping
        entity_name_map = {
            e.id: e.descriptor.name if e.descriptor else e.id
            for e in self.entities
        }
        
        def on_save(new_data):
            try:
                updated = Relationship.model_validate(new_data)
                idx = self.relationships.index(rel)
                self.relationships[idx] = updated
                self.refresh_ui()
                self.update_validation_status()
                
                if self.on_data_changed:
                    self.on_data_changed()
            except Exception as e:
                messagebox.showerror("Validation Error", str(e), parent=self.root)
        
        RelationshipEditor(self.root, rel_data, entity_name_map=entity_name_map, on_save=on_save)
    
    def refresh_ui(self) -> None:
        """Refresh treeviews with current data."""
        if not self.entities_tree or not self.relationships_tree:
            return
        
        # Entities
        for item in self.entities_tree.get_children():
            self.entities_tree.delete(item)
        
        # Map validation issues to entities
        crit_msgs = self.validation_report.get("critical_errors", [])
        warn_msgs = self.validation_report.get("warnings", [])
        
        for ent in self.entities:
            # Simple substring matching for issues
            issues = []
            tag = ""
            
            # Check warnings
            for w in warn_msgs:
                if ent.id in w:
                    issues.append("WARN: " + w.split(":")[-1].strip())
                    tag = "warning"
            
            # Check criticals (override warning tag)
            for c in crit_msgs:
                if ent.id in c:
                    issues.append("ERR: " + c.split(":")[-1].strip())
                    tag = "error"
            
            self.entities_tree.insert(
                "",
                tk.END,
                iid=ent.id,
                values=(
                    ent.id,
                    ent.descriptor.entity_type.value,
                    ent.descriptor.name,
                    "; ".join(issues)
                ),
                tags=(tag,) if tag else ()
            )
        
        # Relationships - clear all items
        try:
            for item in self.relationships_tree.get_children():
                try:
                    self.relationships_tree.delete(item)
                except tk.TclError:
                    pass  # Item might already be deleted
        except Exception:
            pass  # If tree is in bad state, continue anyway
        
        # Build entity ID to name lookup
        entity_names = {
            e.id: e.descriptor.name if e.descriptor else e.id
            for e in self.entities
        }
        
        for rel in self.relationships:
            # Check if item already exists (safety check)
            try:
                existing = self.relationships_tree.exists(rel.id)
                if existing:
                    continue  # Skip if already exists
            except:
                pass  # If exists() fails, continue anyway
            
            issues = []
            tag = ""
            for c in crit_msgs:
                if rel.id in c:
                    issues.append("ERR: " + c.split(":")[-1].strip())
                    tag = "error"
            
            # Resolve entity IDs to names
            source_name = entity_names.get(rel.source_id, rel.source_id)
            target_name = entity_names.get(rel.target_id, rel.target_id)
            
            try:
                self.relationships_tree.insert(
                    "",
                    tk.END,
                    iid=rel.id,
                    values=(
                        source_name,
                        target_name,
                        rel.relationship_type.value,
                        "; ".join(issues)
                    ),
                    tags=(tag,) if tag else ()
                )
            except tk.TclError as e:
                # Item already exists - skip it
                if "already exists" in str(e):
                    continue
                raise
    
    def update_validation_status(self) -> None:
        """Update validation status banner."""
        if not self.validation_frame or not self.validation_label:
            return
        
        crit = len(self.validation_report.get("critical_errors", []))
        warn = len(self.validation_report.get("warnings", []))
        
        # In dark mode/themed mode, we change text color instead of background
        msg = "Validation Passed"
        
        if crit > 0:
            # Error state
            self.validation_label.config(text=f"Validation: {crit} Critical Errors", foreground="#ff5555") # Bright Red text
        elif warn > 0:
            # Warning state
            self.validation_label.config(text=f"Validation: {warn} Warnings", foreground="#ffaa00") # Gold text
        else:
            # Valid state
            self.validation_label.config(text="Validation Passed", foreground="#55ff55") # Bright Green text
    
    def commit_to_database(self) -> bool:
        """Commit current data to database.
        
        Returns:
            True if committed successfully, False otherwise
        """
        if not self.db_path or not self.root:
            return False
        
        # Check for critical errors
        crit_errors = self.validation_report.get("critical_errors", [])
        if len(crit_errors) > 0:
            messagebox.showerror(
                "Cannot Commit",
                f"Fix {len(crit_errors)} critical error(s) before committing:\n\n" + "\n".join(crit_errors[:3]),
                parent=self.root
            )
            return False
        
        if not messagebox.askyesno("Confirm", "Commit changes to database?", parent=self.root):
            return False
        
        try:
            from pyscrai_forge.src.storage import commit_extraction_result
            commit_extraction_result(self.db_path, self.entities, self.relationships)
            messagebox.showinfo("Success", "Committed to database.", parent=self.root)
            return True
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)
            return False
    
    def export_data(self, parent_window) -> bool:
        """Export project data to JSON.
        
        Args:
            parent_window: Parent window for dialogs
            
        Returns:
            True if exported successfully, False otherwise
        """
        file_path = filedialog.asksaveasfilename(
            title="Export Project Data",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=parent_window
        )
        if not file_path:
            return False
        
        try:
            export_data = {
                "entities": [json.loads(e.model_dump_json()) for e in self.entities],
                "relationships": [json.loads(r.model_dump_json()) for r in self.relationships],
                "exported_at": datetime.now(UTC).isoformat(),
                "project_name": self.manifest.name if self.manifest else "Unknown"
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo(
                "Success",
                f"Exported {len(self.entities)} entities and {len(self.relationships)} relationships to {file_path}",
                parent=parent_window
            )
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {e}", parent=parent_window)
            return False
    
    def clear_data(self) -> None:
        """Clear all data."""
        self.entities = []
        self.relationships = []
        self.validation_report = {}
        self.refresh_ui()
        self.update_validation_status()
        
        if self.on_data_changed:
            self.on_data_changed()

