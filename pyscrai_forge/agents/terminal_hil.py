"""Terminal-based Human-in-the-Loop interface for testing HIL workflows.

This provides a simple command-line interface for interacting with agent
pipelines, allowing prompt editing, result review, and approval.
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm

from pyscrai_forge.agents.hil_protocol import HILContext, HILResponse, HILAction


console = Console()


class TerminalHIL:
    """Terminal-based HIL interface.
    
    Usage:
        hil = TerminalHIL()
        manager = ForgeManager(provider, hil_callback=hil.callback)
        await manager.run_extraction_pipeline(text, interactive=True)
    """
    
    def __init__(self, auto_approve_phases: list[str] = None):
        """Initialize terminal HIL.
        
        Args:
            auto_approve_phases: List of phase names to auto-approve without prompting
        """
        self.auto_approve_phases = auto_approve_phases or []
        
    def callback(self, context: HILContext) -> HILResponse:
        """HIL callback that prompts user via terminal.
        
        Args:
            context: Information about current pause point
            
        Returns:
            User's response
        """
        # Auto-approve certain phases if configured
        if context.phase in self.auto_approve_phases:
            return HILResponse(action=HILAction.APPROVE)
        
        # Display phase information
        phase_title = f"{'PRE' if context.is_pre_execution else 'POST'}-EXECUTION: {context.agent_name} ({context.phase})"
        
        console.print()
        console.print(Panel(phase_title, style="bold cyan"))
        
        # Show metadata
        if context.metadata:
            console.print("[dim]Metadata:[/dim]")
            for key, value in context.metadata.items():
                console.print(f"  {key}: {value}")
            console.print()
        
        # Show prompts (if any)
        if context.system_prompt or context.user_prompt:
            console.print("[bold]Prompts:[/bold]")
            if context.system_prompt:
                console.print("[dim]System Prompt (truncated):[/dim]")
                console.print(context.system_prompt[:300] + "..." if len(context.system_prompt) > 300 else context.system_prompt)
            if context.user_prompt:
                console.print("[dim]User Prompt (truncated):[/dim]")
                console.print(context.user_prompt[:300] + "..." if len(context.user_prompt) > 300 else context.user_prompt)
            console.print()
        
        # Show results (if any)
        if context.results is not None:
            console.print(f"[bold]Results:[/bold] ({type(context.results).__name__})")
            if isinstance(context.results, list):
                console.print(f"  Count: {len(context.results)}")
                if len(context.results) > 0:
                    console.print(f"  Sample: {context.results[0] if hasattr(context.results[0], '__dict__') else str(context.results[0])[:100]}")
            elif isinstance(context.results, dict):
                console.print(f"  Keys: {list(context.results.keys())}")
            console.print()
        
        # Show available actions
        actions_str = ", ".join([a.value for a in context.available_actions])
        console.print(f"[dim]Available actions: {actions_str}[/dim]")
        console.print()
        
        # Prompt user for action
        while True:
            action_input = Prompt.ask(
                "[bold green]Action[/bold green]",
                choices=[a.value for a in context.available_actions],
                default="approve"
            )
            
            action = HILAction(action_input)
            
            # Handle each action type
            if action == HILAction.APPROVE:
                console.print("[green]✓ Approved. Continuing...[/green]")
                return HILResponse(action=HILAction.APPROVE)
            
            elif action == HILAction.SKIP:
                if Confirm.ask("Skip this phase?", default=False):
                    console.print("[yellow]⊘ Phase skipped[/yellow]")
                    return HILResponse(action=HILAction.SKIP)
                continue
            
            elif action == HILAction.ABORT:
                if Confirm.ask("Abort entire pipeline?", default=False):
                    console.print("[red]✗ Pipeline aborted[/red]")
                    return HILResponse(action=HILAction.ABORT)
                continue
            
            elif action == HILAction.RETRY:
                console.print("[yellow]↻ Retrying phase...[/yellow]")
                # TODO: Allow prompt editing before retry
                return HILResponse(action=HILAction.RETRY)
            
            elif action == HILAction.EDIT:
                console.print("[yellow]✎ Entering edit mode...[/yellow]")
                edited_response = self._handle_edit(context)
                if edited_response:
                    return edited_response
                # If edit cancelled, continue loop
                continue
            
            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                continue
    
    def _handle_edit(self, context: HILContext) -> HILResponse:
        """Handle edit action - allow user to modify prompts or results.
        
        Returns:
            HILResponse with edits, or None if cancelled
        """
        console.print("\n[bold]Edit Options:[/bold]")
        console.print("1. Edit system prompt")
        console.print("2. Edit user prompt")
        console.print("3. Edit results (JSON)")
        console.print("4. Cancel")
        
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="4")
        
        if choice == "4":
            console.print("[dim]Edit cancelled[/dim]")
            return None
        
        elif choice == "1":
            console.print("[yellow]Current system prompt:[/yellow]")
            console.print(context.system_prompt[:500] + "..." if len(context.system_prompt) > 500 else context.system_prompt)
            console.print("\n[bold]Enter new system prompt (or leave blank to keep current):[/bold]")
            
            # In real implementation, would open editor
            # For now, just return with no edit
            console.print("[dim](Prompt editing not yet implemented - would open editor)[/dim]")
            return None
        
        elif choice == "2":
            console.print("[yellow]Current user prompt:[/yellow]")
            console.print(context.user_prompt[:500] + "..." if len(context.user_prompt) > 500 else context.user_prompt)
            console.print("\n[bold]Enter new user prompt (or leave blank to keep current):[/bold]")
            
            console.print("[dim](Prompt editing not yet implemented - would open editor)[/dim]")
            return None
        
        elif choice == "3":
            if context.results is None:
                console.print("[red]No results to edit (pre-execution phase)[/red]")
                return None
            
            console.print("[yellow]Current results:[/yellow]")
            console.print(Syntax(json.dumps(context.results, default=str, indent=2)[:1000], "json"))
            console.print("\n[bold](Results editing not yet implemented - would open JSON editor)[/bold]")
            return None
        
        return None


__all__ = ["TerminalHIL"]
