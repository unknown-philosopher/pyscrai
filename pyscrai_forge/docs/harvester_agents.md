# PyScrAI Agents Guide

The **Harvester Squad** in `pyscrai_forge` is a team of specialized AI agents designed to extract structured world data from unstructured text.

## Agent Roles

### 1. 🕵️ The Scout (`pyscrai_forge/agents/scout.py`)

*   **Role**: Discovery.
*   **Goal**: "Find everything that looks like a Polity, Actor, or Location."
*   **Input**: Raw text chunk.
*   **Output**: List of `EntityStub` (ID, Name, Type, Description).
*   **Behavior**:
    *   Prioritizes **Recall** over Precision. It's better to find too many things (which can be filtered later) than to miss something.
    *   Does *not* extract detailed stats.
    *   Uses a low temperature (0.1) for consistency.

### 2. 🔬 The Analyst (`pyscrai_forge/agents/analyst.py`)

*   **Role**: Data Mining.
*   **Goal**: "Fill in the stat sheets using the Project Schema."
*   **Input**: `EntityStub`, Raw Text, `ProjectManifest` schema.
*   **Output**: Populated `StateComponent` (resources dictionary).
*   **Behavior**:
    *   **Schema-Aware**: If `project.json` says Actors have "sanity", it looks for sanity. If it says "mana", it looks for mana.
    *   **No Hallucination**: If a field isn't in the text, it leaves it blank/null.

### 3. 🛡️ The Validator (`pyscrai_forge/agents/validator.py`)

*   **Role**: Quality Assurance.
*   **Goal**: "Ensure the graph makes sense."
*   **Input**: List of Entities and Relationships.
*   **Output**: `ValidationReport` (Critical Errors, Warnings).
*   **Checks**:
    *   **Ghost Nodes**: Do relationships point to entities that actually exist?
    *   **Schema Compliance**: Do the extracted stats match the expected types (e.g., is "health" a number)?

### 4. 🗣️ The Reviewer (`pyscrai_forge/agents/reviewer.py`)

*   **Role**: Human-in-the-Loop Interface.
*   **Goal**: "Package data for human approval."
*   **Input**: Validated Entities & Relationships.
*   **Output**: `ReviewPacket` (JSON).
*   **Behavior**:
    *   Creates a serializable packet that a UI can consume.
    *   Does not modify data itself; it prepares it for the user.

### 5. 👔 The Manager (`pyscrai_forge/agents/manager.py`)

*   **Role**: Orchestration.
*   **Goal**: "Run the pipeline."
*   **Behavior**:
    1.  Calls **Scout** to find entities.
    2.  Deduplicates findings.
    3.  Calls **Analyst** for each unique entity (in parallel).
    4.  Extracts **Relationships** (currently a manager-level task).
    5.  Calls **Validator**.
    6.  Calls **Reviewer** to save the packet.

## Extending Agents

To add a new agent (e.g., a "Cartographer" to generate map coordinates):

1.  Create `pyscrai_forge/agents/cartographer.py`.
2.  Define the class `CartographerAgent`.
3.  Implement a method that takes text/entities and returns `SpatialComponent` data.
4.  Add it to `HarvesterOrchestrator` in `manager.py`.

## Prompt Engineering

Prompts are located in `pyscrai_forge/harvester/prompts.py`.
*   **Scout Prompt**: Focuses on identifying proper nouns and categorizing them.
*   **Analyst Prompt**: Dynamic! It injects the specific JSON schema for the entity type being analyzed.
