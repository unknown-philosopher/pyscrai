"""CLI entrypoint for PyScrAI Engine.

Provides simple commands to run or step the simulation.

Usage (after installing editable):
    pyscrai-engine run <project_path> [--max-turns N] [--with-agents]
    pyscrai-engine step <project_path> [--with-agents]
    pyscrai-engine status <project_path>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pyscrai_engine.engine import SimulationEngine


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyscrai-engine", description="PyScrAI Engine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run simulation for N turns (default 100)")
    run_p.add_argument("project_path", type=Path, help="Path to project directory")
    run_p.add_argument("--max-turns", type=int, default=100, help="Max turns to run")
    run_p.add_argument("--with-agents", action="store_true", help="Enable rule-based agents to generate intentions")

    step_p = sub.add_parser("step", help="Execute exactly one turn")
    step_p.add_argument("project_path", type=Path, help="Path to project directory")
    step_p.add_argument("--with-agents", action="store_true", help="Enable rule-based agents to generate intentions")

    status_p = sub.add_parser("status", help="Show project summary")
    status_p.add_argument("project_path", type=Path, help="Path to project directory")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        engine = SimulationEngine(args.project_path)
        engine.initialize()
        if args.with_agents:
            engine.enable_agents = True
            print("[CLI] Rule-based agents enabled")
        engine.run(max_turns=args.max_turns)
    elif args.command == "step":
        engine = SimulationEngine(args.project_path)
        engine.initialize()
        if args.with_agents:
            engine.enable_agents = True
            print("[CLI] Rule-based agents enabled")
        engine.step()
    elif args.command == "status":
        engine = SimulationEngine(args.project_path)
        engine.initialize()
        print(f"Project: {engine.manifest.name}")
        print(f"Schema version: {engine.manifest.schema_version}")
        print(f"Entities: {len(engine.entities)}")
        print(f"Relationships: {len(engine.relationships)}")
        print(f"Snapshot interval: {engine.manifest.snapshot_interval}")
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()
