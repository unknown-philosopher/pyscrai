PyScrAI|Forge: The Vision for V1.0.0

1. Executive Summary

PyScrAI is not a static database tool, nor is it a rigid game engine. It is a Chimera: a living bridge between historical/fictional data and interactive simulation. The Forge is the crucible where raw data (intel, lore, prompts) is hammered into a functional world state. Version 1.0.0 transforms the Forge from a manual editor into an Agentic Ecosystem where the user and the AI "Architect" co-create through an interactive, non-linear loop of discovery, extraction, and roleplay.

2. The Core Philosophy: "The Forge"

Unlike traditional simulation builders that follow a linear path (Input -> Parse -> Output), the PyScrAI|Forge operates as a Co-operative Back-and-Forth.

Dynamic Hammering: The Architect agent doesn't just extract data; it questions the user. "The text implies a high degree of corruption in the Ministry of Defense. Should we add a 'corruption' stat to our Polity schema?"

Modular Agnosticism: Every project is its own system. The "truth" of a project is defined by its custom ProjectManifest schemas, not hardcoded logic.

The Accordion Effect: The ability to instantly shift scale.

Macro: Strategic theatres, national GDP, diplomatic alliances.

Meso: Battalions, supply lines, city-state politics.

Micro: Individual actors, personal health, specific inventories.

3. The Agentic Workforce

V1.0.0 introduces a hierarchical multi-agent system that wraps the existing Harvester pipeline:

I. The Architect (The Sovereign)

The primary interface for the user. It manages the ProjectManifest. It is responsible for:

Interviewing the user to define the world's rules (Schemas).

Creating templates and prefabs for recurring scenario types.

Translating abstract user intent into structured tool-calls (e.g., create_polity, define_stat).

II. The Promptsmith (The Meta-Agent)

The "Cognitive Layer" that ensures the Harvester is project-aware.

It dynamically generates the system prompts for the Scout and Analyst agents based on the project's specific genre and schema.

III. The Harvester Squad (The Laborers)

The Scout: High-recall discovery of potential nodes.

The Analyst: Schema-driven data mining.

The Validator: Graph integrity and sanity checks.

4. Interactive Possession & Simulation

The most ambitious feature of V1.0.0 is the transition from Building to Acting.

Node Possession: At any point, the Architect or User can "possess" an entity (Actor or Polity).

The Cognitive Module: Uses the existing CognitiveComponent and MemoryContext to drive real-time roleplay.

Experimental Simulations: Run "Pre-Sims" or "Preludes" to test world logic. These sessions generate Event logs (Turns) using the pyscrai_core event system.

The Choice: At the conclusion of a roleplay session, the user decides: "Is this canon?" If yes, the Events are committed to the world.db, evolving the project's state permanently.

5. Technical Implementation Layer

This vision leverages the existing pyscrai_core architecture:

ECS Purity: Data lives in components; behavior is injected by agents.

Authoritative State: StateComponent (resources_json) remains the singular source of truth for facts, while MemoryChunk remains the lossy perception used by roleplaying agents.

Persistence: All "canon" events flow into the SQLite world.db, ensuring that the world "remembers" the outcome of every interactive session.

6. The Roadmap to 1.0.0

Instantiation of the Architect Agent: Transition the Project Wizard to a conversational loop with tool-access.

Implementation of the "Possession" Toggle: A UI/CLI mode that switches interaction from "Define" to "Act."

Advanced RAG/Memory Integration: Connecting ChromaDB storage directly to the possession sessions for contextual world-knowledge.

Linguistic Summarization: Automatically generating rich narrative summaries of the world state after any significant simulation event.

"Only the imagination and the availability of data define the limits of the world."