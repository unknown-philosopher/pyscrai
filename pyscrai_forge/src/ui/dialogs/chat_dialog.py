"""Interactive chat dialog for refining extracted entities using natural language.

This dialog appears after extraction completes, allowing users to refine entities
through conversational commands like "Merge entity A into entity B" or
"Delete entity X".
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship
    from pyscrai_forge.agents.user_proxy import UserProxyAgent


class ChatDialog(tk.Toplevel):
    """Dialog for natural language entity refinement."""
    
    def __init__(
        self,
        parent: tk.Tk,
        entities: list["Entity"],
        relationships: list["Relationship"],
        user_proxy: "UserProxyAgent",
        on_operation_executed: Optional[Callable[[list["Entity"], list["Relationship"]], None]] = None
    ):
        """
        Initialize the chat dialog.
        
        Args:
            parent: Parent window
            entities: Current list of entities (will be modified in place)
            relationships: Current list of relationships (will be modified in place)
            user_proxy: UserProxyAgent instance for processing commands
            on_operation_executed: Callback(entities, relationships) when an operation completes
        """
        super().__init__(parent)
        self.title("Refine Entities - Chat")
        self.geometry("700x600")
        self.transient(parent)
        
        self.entities = entities
        self.relationships = relationships
        self.user_proxy = user_proxy
        self.on_operation_executed = on_operation_executed
        
        self._create_ui()
        
        # Add welcome message
        self._add_system_message(
            f"Ready to refine your entities! You have {len(entities)} entities and "
            f"{len(relationships)} relationships.\n\n"
            "Try commands like:\n"
            "• 'Merge entity A into entity B'\n"
            "• 'Delete entity X'\n"
            "• 'Create a relationship between A and B'\n"
            "• 'Show me all actors'\n"
            "• 'Change entity A's description to...'"
        )
    
    def _create_ui(self):
        """Build the dialog UI."""
        # Conversation area (scrollable)
        conv_frame = ttk.LabelFrame(self, text="Conversation", padding=10)
        conv_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.conversation_text = scrolledtext.ScrolledText(
            conv_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 10)
        )
        self.conversation_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for different message types
        self.conversation_text.tag_config("user", foreground="#4A9EFF")
        self.conversation_text.tag_config("assistant", foreground="#00AA00")
        self.conversation_text.tag_config("system", foreground="#888888", font=("Consolas", 9, "italic"))
        self.conversation_text.tag_config("error", foreground="#FF5555")
        
        # Input area
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.input_entry = ttk.Entry(input_frame, font=("Consolas", 10))
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", lambda e: self._send_message())
        
        send_btn = ttk.Button(input_frame, text="Send", command=self._send_message, width=10)
        send_btn.pack(side=tk.RIGHT)
        
        # Status bar
        self.status_label = ttk.Label(self, text="Ready", foreground="gray")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
        
        # Focus on input
        self.input_entry.focus()
    
    def _add_system_message(self, message: str):
        """Add a system message to the conversation."""
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.insert(tk.END, f"[System] {message}\n\n", "system")
        self.conversation_text.config(state=tk.DISABLED)
        self.conversation_text.see(tk.END)
    
    def _add_user_message(self, message: str):
        """Add a user message to the conversation."""
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.insert(tk.END, f"You: {message}\n", "user")
        self.conversation_text.config(state=tk.DISABLED)
        self.conversation_text.see(tk.END)
    
    def _add_assistant_message(self, message: str):
        """Add an assistant message to the conversation."""
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.insert(tk.END, f"Assistant: {message}\n\n", "assistant")
        self.conversation_text.config(state=tk.DISABLED)
        self.conversation_text.see(tk.END)
    
    def _add_error_message(self, message: str):
        """Add an error message to the conversation."""
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.insert(tk.END, f"Error: {message}\n\n", "error")
        self.conversation_text.config(state=tk.DISABLED)
        self.conversation_text.see(tk.END)
    
    def _send_message(self):
        """Process and send the user's message."""
        user_input = self.input_entry.get().strip()
        if not user_input:
            return
        
        # Clear input
        self.input_entry.delete(0, tk.END)
        
        # Add user message to conversation
        self._add_user_message(user_input)
        
        # Update status
        self.status_label.config(text="Processing...", foreground="blue")
        self.update()
        
        # Process command asynchronously
        import asyncio
        import threading
        
        def process_async():
            """Run async command processing in a separate thread."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.user_proxy.process_command(user_input, self.entities, self.relationships)
                    )
                    # Schedule UI update in main thread
                    self.after(0, lambda: self._handle_result(result))
                finally:
                    loop.close()
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: self._handle_error(msg))
        
        thread = threading.Thread(target=process_async, daemon=True)
        thread.start()
    
    def _handle_result(self, result):
        """Handle the result from UserProxyAgent.
        
        Args:
            result: Either a dict with operation data, or a string message
        """
        self.status_label.config(text="Ready", foreground="gray")
        
        if isinstance(result, dict):
            if result.get("operation") == "error":
                self._add_error_message(result.get("message", "Unknown error"))
            else:
                # Execute the operation using operation handlers
                from pyscrai_forge.src.app.operation_handlers import OperationHandler
                handler = OperationHandler(self.entities, self.relationships)
                result_msg, success = handler.execute_operation(result)
                
                if success:
                    self._add_assistant_message(result_msg)
                    # Update entities/relationships counts in status
                    self.status_label.config(
                        text=f"{len(self.entities)} entities, {len(self.relationships)} relationships",
                        foreground="gray"
                    )
                    
                    # Notify callback to refresh UI
                    if self.on_operation_executed:
                        self.on_operation_executed(self.entities, self.relationships)
                else:
                    self._add_error_message(result_msg)
        else:
            # String response (fallback - shouldn't happen with new UserProxyAgent, but handle gracefully)
            self._add_assistant_message(str(result))
    
    def _handle_error(self, error_msg: str):
        """Handle an error during processing."""
        self.status_label.config(text="Error", foreground="red")
        self._add_error_message(error_msg)
    
    def update_entities_and_relationships(self, entities: list["Entity"], relationships: list["Relationship"]):
        """Update the entities and relationships lists after an operation."""
        self.entities = entities
        self.relationships = relationships

