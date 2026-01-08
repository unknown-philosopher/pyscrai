"""Data and entity operations for PyScrAI|Forge.

This module contains the DataOperationsMixin class with all data-related
callback methods extracted from main_app.py for better separation of concerns.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Optional

from .state_manager import AppState
from ..ui.dialogs import ProgressDialog


class DataOperationsMixin:
    """Mixin class for data and entity operations.
    
    This mixin provides all data-related callback methods that can be
    mixed into the main ReviewerApp class. Methods expect access to:
    - self.project_controller
    - self.data_manager
    - self.state_manager
    - self.root
    - self.logger
    - self._refresh_foundry_ui (from main class)
    """
    
    # Data callbacks
    def _on_import_file(self) -> None:
        """Handle import file action."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load or create a project first.", parent=self.root)
            return
        
        from pyscrai_forge.src.ui.import_dialog import ImportDialog
        from pyscrai_forge.src.staging import StagingService
        
        # Create staging service for source pool management
        staging_service = StagingService(self.project_controller.current_project)
        
        def on_import(text, metadata, file_path, reset_counters=False):
            # Use ForgeManager to extract entities
            import asyncio
            import threading
            from pyscrai_forge.agents.manager import ForgeManager
            from pyscrai_forge.prompts.core import Genre
            from pyscrai_core.llm_interface import create_provider
            from pathlib import Path
            import os
            
            # Get provider settings from project manifest instead of .env
            # Reload manifest from disk to ensure we have the latest settings
            self.project_controller._load_manifest()
            manifest = self.project_controller.manifest
            if not manifest:
                messagebox.showerror("Error", "No project manifest found. Please create or load a project first.")
                return
            
            # Get API key from environment (only API keys should remain in .env)
            provider_name = manifest.llm_provider
            env_key_map = {
                "openrouter": "OPENROUTER_API_KEY",
                "cherry": "CHERRY_API_KEY",
                "lm_studio": "LM_STUDIO_API_KEY",
                "lm_proxy": "LM_PROXY_API_KEY",
            }
            api_key = os.getenv(env_key_map.get(provider_name, ""), "not-needed")
            
            # Get provider/model info for status
            provider_name = manifest.llm_provider
            model_name = manifest.llm_default_model
            status_text = f"Provider: {provider_name} | Model: {model_name}"
            
            # Create progress dialog using reusable class
            progress_dialog = ProgressDialog(
                parent=self.root,
                title="Extracting Entities",
                message="Initializing LLM provider...",
                status=status_text
            )
            
            result_container = {"entities": None, "relationships": None, "report": None, "error": None}
            
            async def run_extraction():
                try:
                    # Store provider and model for consistent display
                    provider_name = manifest.llm_provider
                    model_name = manifest.llm_default_model
                    
                    progress_dialog.update_message("Connecting to LLM provider...")
                    
                    # Create provider from project manifest settings
                    provider = create_provider(
                        provider_name,
                        api_key=api_key,
                        base_url=manifest.llm_base_url,
                        timeout=60.0
                    )
                    
                    # Store the default model on the provider
                    if hasattr(provider, 'default_model'):
                        provider.default_model = model_name
                    
                    model = model_name
                    
                    # Use current project path if available
                    project_path = None
                    if self.project_controller.current_project:
                        project_path = self.project_controller.current_project
                    
                    # Reset ID counters if requested - do this AFTER getting project path
                    # but BEFORE creating ForgeManager (which loads the project and counters)
                    if reset_counters:
                        from pyscrai_core import reset_id_counters
                        from pyscrai_core.models import set_id_counters_path
                        
                        # Set the counters path first so reset can write to the file
                        if project_path:
                            set_id_counters_path(project_path / ".id_counters.json")
                        
                        reset_id_counters()
                        progress_dialog.update_all(
                            message="ID counters reset",
                            detail="Starting from ENTITY_001 and REL_001"
                        )
                    
                    async with provider:
                        manager = ForgeManager(provider, project_path=project_path, hil_callback=None)
                        
                        # Get the template from the project manifest if available
                        template_name = None
                        if manager.controller and manager.controller.manifest:
                            template_name = manager.controller.manifest.template
                        
                        # Run extraction pipeline (creates review packet)
                        progress_dialog.update_message("Running extraction pipeline...")
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                            tmp_path = Path(tmp.name)
                        
                        try:
                            # Check for verbose mode via environment variable or config
                            import os
                            verbose = os.getenv("PYSCRAI_VERBOSE", "").lower() in ("1", "true", "yes")
                            
                            # Foundry phase: Only extract entities, skip relationships
                            packet_path = await manager.run_extraction_pipeline(
                                text=text,
                                genre=Genre.GENERIC,
                                output_path=tmp_path,
                                template_name=template_name,
                                verbose=verbose,
                                extract_relationships=False  # Foundry only extracts entities
                            )
                            
                            # Load the packet to get entities and relationships
                            import json
                            with open(packet_path, 'r', encoding='utf-8') as f:
                                packet = json.load(f)
                            
                            # Convert back to Entity objects (Foundry only extracts entities)
                            from pyscrai_core import Entity
                            entities = []
                            for e_data in packet.get('entities', []):
                                entities.append(Entity.model_validate(e_data))
                            
                            # Foundry phase doesn't extract relationships
                            relationships = []
                            
                            # Extract validation report from packet
                            from pyscrai_forge.agents.validator import ValidationReport
                            validation_data = packet.get('validation_report', {})
                            report = ValidationReport(
                                critical_errors=validation_data.get('critical_errors', []),
                                warnings=validation_data.get('warnings', [])
                            )
                            
                            return entities, relationships, report
                        except ValueError as ve:
                            # Handle pipeline failures (e.g., Scout phase failed)
                            raise Exception(f"Extraction pipeline failed: {ve}")
                        
                except Exception as e:
                    raise Exception(f"LLM connection or extraction failed: {str(e)}")
            
            def run_async_in_thread():
                """Run the async extraction in a separate thread with its own event loop."""
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        entities, relationships, report = loop.run_until_complete(run_extraction())
                        result_container["entities"] = entities
                        result_container["relationships"] = relationships
                        result_container["report"] = report
                    finally:
                        loop.close()
                except Exception as e:
                    result_container["error"] = str(e)
                
                # Schedule cleanup in main thread
                self.root.after(0, finish_extraction)
            
            def finish_extraction():
                """Handle extraction results in main thread."""
                try:
                    progress_dialog.close()
                except:
                    pass
                
                if result_container["error"]:
                    messagebox.showerror("Extraction Error", result_container["error"], parent=self.root)
                    return
                
                entities = result_container["entities"]
                relationships = result_container["relationships"]
                report = result_container["report"]
                
                # Load into data manager
                self.data_manager.entities = entities
                self.data_manager.relationships = relationships
                self.data_manager.validation_report = report.model_dump() if hasattr(report, 'model_dump') else {}
                
                # Transition to Foundry phase to show results
                self.state_manager.transition_to(AppState.PHASE_FOUNDRY)
                
                # Update FoundryPanel with extracted data
                self._refresh_foundry_ui()
                
                if len(entities) == 0:
                    messagebox.showwarning(
                        "No Entities Found",
                        f"No entities were extracted from {file_path}.\n\n"
                        "Possible reasons:\n"
                        "• Text may not contain recognizable entities\n"
                        "• LLM connection issues (check terminal for errors)\n"
                        "• Model may need different prompting"
                    )
                else:
                    out_path = None
                    if self.project_controller.current_project:
                        import datetime
                        import re
                        data_dir = self.project_controller.current_project / "data"
                        data_dir.mkdir(exist_ok=True)
                        src_name = Path(file_path).stem if file_path else "imported"
                        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
                        safe_src = re.sub(r'[^a-zA-Z0-9_\-]', '_', src_name)
                        out_name = f"entity_components_{timestamp}_{safe_src}.json"
                        out_path = data_dir / out_name
                        backup_data = {
                            "entities": [json.loads(e.model_dump_json()) for e in entities],
                            "relationships": [json.loads(r.model_dump_json()) for r in relationships],
                            "validation_report": report.model_dump() if hasattr(report, 'model_dump') else {}
                        }
                        try:
                            with open(out_path, "w", encoding="utf-8") as f:
                                json.dump(backup_data, f, indent=2)
                        except Exception as e:
                            print(f"[WARN] Failed to save backup JSON: {e}")
                    
                    messagebox.showinfo(
                        "Import Complete",
                        f"Extracted {len(entities)} entities from {file_path}.\n\n"
                        f"Validation: {'✓ Passed' if report.is_valid else f'✗ {len(report.critical_errors)} errors'}\n\n"
                        f"Backup saved to: {out_path if out_path else '[no project loaded]'}"
                    )
            
            # Start extraction in background thread
            thread = threading.Thread(target=run_async_in_thread, daemon=True)
            thread.start()
        
        ImportDialog(self.root, on_import=on_import, staging_service=staging_service)
    
    def _on_extract_from_pool(self) -> None:
        """Extract entities from all active sources in the pool."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load or create a project first.", parent=self.root)
            return
        
        from pyscrai_forge.src.staging import StagingService
        
        staging_service = StagingService(self.project_controller.current_project)
        active_sources = staging_service.get_active_sources()
        
        if not active_sources:
            messagebox.showwarning(
                "No Sources",
                "No active source files in the pool.\n\nUse 'Add Files...' to add source data first.",
                parent=self.root
            )
            return
        
        # Get combined text from active sources
        combined_text = staging_service.get_combined_source_text()
        total_chars = sum(s.get('char_count', 0) for s in active_sources)
        
        # Confirm extraction
        if not messagebox.askyesno(
            "Extract from Source Pool",
            f"Extract entities from {len(active_sources)} active source(s)?\n\n"
            f"Total characters: {total_chars:,}\n\n"
            "This will run the entity extraction pipeline.",
            parent=self.root
        ):
            return
        
        # Trigger extraction with combined text
        self._run_extraction(
            text=combined_text,
            metadata={
                "source_count": len(active_sources),
                "source_files": [s.get("original_filename", s["id"]) for s in active_sources],
                "total_chars": total_chars
            },
            file_path=None,
            reset_counters=False,
            staging_service=staging_service
        )
    
    def _run_extraction(
        self,
        text: str,
        metadata: dict,
        file_path,
        reset_counters: bool = False,
        staging_service=None
    ) -> None:
        """Run entity extraction pipeline.
        
        Args:
            text: Text content to extract from
            metadata: Metadata about the source
            file_path: Original file path (if single file)
            reset_counters: Whether to reset ID counters
            staging_service: Optional staging service for marking sources as extracted
        """
        import asyncio
        import threading
        from pyscrai_forge.agents.manager import ForgeManager
        from pyscrai_forge.prompts.core import Genre
        from pyscrai_core.llm_interface import create_provider
        from pathlib import Path
        import os
        
        # Get provider settings from project manifest
        self.project_controller._load_manifest()
        manifest = self.project_controller.manifest
        if not manifest:
            messagebox.showerror("Error", "No project manifest found. Please create or load a project first.")
            return
        
        # Get API key from environment
        provider_name = manifest.llm_provider
        env_key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "cherry": "CHERRY_API_KEY",
            "lm_studio": "LM_STUDIO_API_KEY",
            "lm_proxy": "LM_PROXY_API_KEY",
        }
        api_key = os.getenv(env_key_map.get(provider_name, ""), "not-needed")
        
        # Get provider/model info for status
        provider_name = manifest.llm_provider
        model_name = manifest.llm_default_model
        status_text = f"Provider: {provider_name} | Model: {model_name}"
        
        # Create progress dialog using reusable class
        progress_dialog = ProgressDialog(
            parent=self.root,
            title="Extracting Entities",
            message="Initializing LLM provider...",
            status=status_text
        )
        
        result_container = {"entities": None, "relationships": None, "report": None, "error": None}
        
        async def run_extraction():
            try:
                progress_dialog.update_message("Connecting to LLM provider...")
                
                provider = create_provider(
                    provider_name,
                    api_key=api_key,
                    base_url=manifest.llm_base_url,
                    timeout=60.0
                )
                
                if hasattr(provider, 'default_model'):
                    provider.default_model = model_name
                
                model = model_name
                project_path = self.project_controller.current_project
                
                if reset_counters:
                    from pyscrai_core import reset_id_counters
                    from pyscrai_core.models import set_id_counters_path
                    
                    if project_path:
                        set_id_counters_path(project_path / ".id_counters.json")
                    
                    reset_id_counters()
                    progress_dialog.update_all(
                        message="ID counters reset",
                        detail="Starting from ENTITY_001 and REL_001"
                    )
                
                async with provider:
                    manager = ForgeManager(provider, project_path=project_path, hil_callback=None)
                    
                    # Get the template from the project manifest if available
                    template_name = None
                    if manager.controller and manager.controller.manifest:
                        template_name = manager.controller.manifest.template
                    
                    progress_dialog.update_message("Running extraction pipeline...")
                    
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                    
                    try:
                        # Check for verbose mode via environment variable or config
                        verbose = os.getenv("PYSCRAI_VERBOSE", "").lower() in ("1", "true", "yes")
                        
                        # Foundry phase: Only extract entities, skip relationships
                        packet_path = await manager.run_extraction_pipeline(
                            text=text,
                            genre=Genre.GENERIC,
                            output_path=tmp_path,
                            template_name=template_name,
                            verbose=verbose,
                            extract_relationships=False  # Foundry only extracts entities
                        )
                        
                        # Load the packet to get entities and relationships
                        import json
                        with open(packet_path, 'r', encoding='utf-8') as f:
                            packet = json.load(f)
                        
                        # Convert back to Entity objects (Foundry only extracts entities)
                        from pyscrai_core import Entity
                        entities = []
                        for e_data in packet.get('entities', []):
                            entities.append(Entity.model_validate(e_data))
                        
                        # Foundry phase doesn't extract relationships
                        relationships = []
                        
                        # Extract validation report from packet
                        from pyscrai_forge.agents.validator import ValidationReport
                        validation_data = packet.get('validation_report', {})
                        report = ValidationReport(
                            critical_errors=validation_data.get('critical_errors', []),
                            warnings=validation_data.get('warnings', [])
                        )
                        
                        return entities, relationships, report
                    except ValueError as ve:
                        # Handle pipeline failures (e.g., Scout phase failed)
                        raise Exception(f"Extraction pipeline failed: {ve}")
                    
            except Exception as e:
                raise Exception(f"LLM connection or extraction failed: {str(e)}")
        
        def run_async_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    entities, relationships, report = loop.run_until_complete(run_extraction())
                    result_container["entities"] = entities
                    result_container["relationships"] = relationships
                    result_container["report"] = report
                finally:
                    loop.close()
            except Exception as e:
                result_container["error"] = str(e)
            
            self.root.after(0, finish_extraction)
        
        def finish_extraction():
            try:
                progress_dialog.close()
            except:
                pass
            
            if result_container["error"]:
                messagebox.showerror("Extraction Failed", result_container["error"], parent=self.root)
                return
            
            entities = result_container["entities"]
            relationships = result_container["relationships"]
            report = result_container["report"]
            
            if not entities:
                messagebox.showwarning(
                    "No Entities Found",
                    f"No entities were extracted from the source(s).\n\n"
                    "Possible reasons:\n"
                    "• Text may not contain recognizable entities\n"
                    "• LLM connection issues (check terminal for errors)\n"
                    "• Model may need different prompting",
                    parent=self.root
                )
                return
            
            # Load into data manager
            self.data_manager.entities = entities
            self.data_manager.relationships = relationships or []
            self.data_manager.validation_report = report.model_dump() if hasattr(report, 'model_dump') else {}
            
            # Transition to Foundry phase to show results
            self.state_manager.transition_to(AppState.PHASE_FOUNDRY)
            
            # Update FoundryPanel with extracted data
            self._refresh_foundry_ui()
            
            # Mark sources as extracted if staging service provided
            if staging_service and metadata.get("source_files"):
                try:
                    for source in staging_service.get_active_sources():
                        staging_service.mark_source_extracted(source["id"])
                except Exception as e:
                    print(f"Warning: Failed to mark sources as extracted: {e}")
            
            # Save backup
            import json
            out_path = None
            if self.project_controller.current_project:
                import datetime
                import re
                data_dir = self.project_controller.current_project / "data"
                data_dir.mkdir(exist_ok=True)
                src_name = Path(file_path).stem if file_path else "pool_extract"
                timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
                safe_src = re.sub(r'[^a-zA-Z0-9_\-]', '_', src_name)
                out_name = f"entity_components_{timestamp}_{safe_src}.json"
                out_path = data_dir / out_name
                backup_data = {
                    "entities": [json.loads(e.model_dump_json()) for e in entities],
                    "relationships": [json.loads(r.model_dump_json()) for r in relationships] if relationships else [],
                    "validation_report": report.model_dump() if hasattr(report, 'model_dump') else {}
                }
                try:
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(backup_data, f, indent=2)
                except Exception as e:
                    print(f"[WARN] Failed to save backup JSON: {e}")
            
            source_info = metadata.get("source_files", [file_path.name if file_path else "unknown"])
            source_count = len(source_info) if isinstance(source_info, list) else 1
            messagebox.showinfo(
                "Extraction Complete",
                f"Extracted {len(entities)} entities from {source_count} source(s).\n\n"
                f"Validation: {'✓ Passed' if report.is_valid else f'✗ {len(report.critical_errors)} errors'}\n\n"
                f"Backup saved to: {out_path if out_path else '[no project loaded]'}",
                parent=self.root
            )
            
            # Refresh source list in Foundry UI if it exists
            if hasattr(self.state_manager, 'foundry_panel'):
                try:
                    self.state_manager.foundry_panel._refresh_sources_list()
                except:
                    pass
        
        thread = threading.Thread(target=run_async_in_thread, daemon=True)
        thread.start()
    
    def _on_load_data_file(self) -> None:
        """Handle load data file action."""
        if self.data_manager.load_from_file(self.root):
            # Transition to Foundry phase to show loaded data
            self.state_manager.transition_to(AppState.PHASE_FOUNDRY)
            # Update FoundryPanel with loaded data
            self._refresh_foundry_ui()
    
    def _on_add_entity(self) -> None:
        """Handle add entity action."""
        self.data_manager.add_entity()
    
    def _on_delete_selected_entity(self) -> None:
        """Handle delete selected entity action."""
        self.data_manager.delete_selected_entity()
    
    def _on_edit_entity(self, entity_id: Optional[str] = None) -> None:
        """Handle edit entity action.
        
        Args:
            entity_id: Optional entity ID to edit. If not provided, uses selection.
        """
        self.data_manager.edit_entity(entity_id=entity_id)
    
    def _on_add_relationship(self) -> None:
        """Handle add relationship action."""
        self.data_manager.add_relationship()
    
    def _on_delete_selected_relationship(self) -> None:
        """Handle delete selected relationship action."""
        self.data_manager.delete_selected_relationship()
    
    def _on_edit_relationship(self) -> None:
        """Handle edit relationship action."""
        self.data_manager.edit_relationship()
    
    def _on_commit_to_db(self) -> None:
        """Handle commit to database action."""
        self.data_manager.commit_to_database()
    
    def _on_export_data(self) -> None:
        """Handle export data action."""
        self.data_manager.export_data(self.root)
    
    def _on_edit_components(self) -> None:
        """Handle edit components action - navigates to Foundry phase."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load a project first.", parent=self.root)
            return
        self.state_manager.transition_to(AppState.PHASE_FOUNDRY)
        self._refresh_foundry_ui()
        self._refresh_foundry_ui()
    
    def _on_refine_components(self) -> None:
        """Handle refine components action - opens chat dialog for entity refinement."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load a project first.", parent=self.root)
            return
        
        # Get current entities and relationships from data manager
        entities = self.data_manager.entities
        relationships = self.data_manager.relationships
        
        if not entities:
            messagebox.showinfo("No Entities", "No entities to refine. Import or create some first.", parent=self.root)
            return
        
        # Open chat dialog for refinement
        from pyscrai_forge.src.ui.dialogs.chat_dialog import ChatDialog
        
        # Try to create a UserProxyAgent with LLM provider
        user_proxy = None
        try:
            from pyscrai_forge.agents.user_proxy import UserProxyAgent
            from pyscrai_core.llm_interface import create_provider
            import os
            
            # Get provider settings from project manifest
            manifest = self.project_controller.manifest
            if manifest:
                provider_name = manifest.llm_provider
                env_key_map = {
                    "openrouter": "OPENROUTER_API_KEY",
                    "cherry": "CHERRY_API_KEY",
                    "lm_studio": "LM_STUDIO_API_KEY",
                    "lm_proxy": "LM_PROXY_API_KEY",
                }
                api_key = os.getenv(env_key_map.get(provider_name, ""), "not-needed")
                
                provider = create_provider(
                    manifest.llm_provider,
                    api_key=api_key,
                    base_url=manifest.llm_base_url,
                    timeout=60.0
                )
                
                if hasattr(provider, 'default_model'):
                    provider.default_model = manifest.llm_default_model
                
                model = manifest.llm_default_model
                user_proxy = UserProxyAgent(provider, model)
        except Exception as e:
            self.logger.warning(f"Could not create UserProxyAgent: {e}. Chat will be limited.")
        
        # For now, use a simple callback that updates the data manager
        def on_operation_executed(updated_entities, updated_relationships):
            self.data_manager.entities = updated_entities
            self.data_manager.relationships = updated_relationships
            self.data_manager.refresh_ui()
            self.logger.info(f"Refined entities: {len(updated_entities)} entities, {len(updated_relationships)} relationships")
        
        # Create and show chat dialog
        chat_dialog = ChatDialog(
            self.root,
            entities=entities,
            relationships=relationships,
            user_proxy=user_proxy,
            on_operation_executed=on_operation_executed
        )

