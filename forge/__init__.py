"""PyScrAI Forge package."""

from .core.event_bus import EventBus

# AppController requires fletx, so import it lazily/optionally
try:
    from .core.app_controller import AppController
    __all__ = ["AppController", "EventBus"]
except ImportError:
    # fletx not installed (e.g., in test environments)
    __all__ = ["EventBus"]
