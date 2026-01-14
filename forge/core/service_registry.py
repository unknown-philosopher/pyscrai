"""Service registry for cross-module access to initialized services."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from forge.domain.session.session_manager import SessionManager

# Global reference to session manager
_session_manager: Optional["SessionManager"] = None


def set_session_manager(session_manager: "SessionManager") -> None:
    """Set the global session manager instance."""
    global _session_manager
    _session_manager = session_manager


def get_session_manager() -> Optional["SessionManager"]:
    """Get the global session manager instance."""
    return _session_manager