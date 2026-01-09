"""
Entry point for running Forge as a module.

Usage:
    python -m forge
    python -m forge --project my_project
    python -m forge --help
"""

from forge.app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
