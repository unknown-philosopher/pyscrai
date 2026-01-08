Here is the **concise, fully tied-in revision** with your final correction applied (Phase 3 → **SYNTH**) and the nomenclature decision cleanly integrated into the original document. I’ve only changed what was necessary and tightened language where it improved clarity.

---

## Forge 3.0 — Design Vision & Structural Changes

The goal is to overhaul the Forge into version 3.0, beginning with a clear reset of the core design philosophy—particularly around data extraction, pipeline structure, and UI nomenclature.

### Core Problem: Data Extraction

Referencing the annotated screenshot, the primary failure in the current system lies in data extraction. The attempt to separate **entity extraction** from **relationship extraction** has been unsuccessful and has introduced systemic issues. The extraction model used in version 1.0 was substantially more stable and effective.

Forge 3.0 will return to a **unified extraction model**, conceptually similar to 1.0, while preserving the broader multi-phase pipeline introduced later.

### Pipeline Structure (High-Level)

The multi-phase pipeline will remain intact. Although the legacy concepts of the Foundry and Loom remain valid at a functional level, their *data origin* will be unified. The **UI-level editing of entities and relationships will continue to be separate**, but both will draw from the same authoritative source.

### Phase Zero: Unified Extraction Pipeline

Forge 3.0 introduces a new **Phase Zero pipeline**, which becomes the single entry point for all source data.

In Phase Zero:

* Entities and relationships are extracted **together**, in one coherent pass.
* The extracted data is **staged for approval**.
* Once approved, the data is **persistently and permanently stored**.
* This approved dataset becomes the authoritative source for:

  * Entity systems
  * Relationship systems
  * Embedding / memory systems (subject to later optimization)

This guarantees that all assistant modules operate on **consistent, updateable, shared data**.

### Update, History, and Reset Requirements

After initial staging:

* The system must support **incremental updates** to staged data.
* Updates must **not delete prior data**.
* Instead, the system must:

  * Maintain a **historical log** of changes
  * Intelligently **deduplicate unchanged entities, attributes, and relationships**
  * Preserve stable data across additional sources

Phase Zero must also include a **RESET function** that:

* Fully clears all extracted and staged data
* Preserves only:

  * `project.json` schemas
  * Project configuration and settings

This enables true clean re-ingestion without structural loss.

### Templates, Compatibility, and Version Boundaries

* Default templates have been updated to what were previously test templates.
* This is a project-level setting and the codebase already adheres to it.
* No impact is expected from this change.

**Backwards compatibility is explicitly not desired.**
Forge 3.0 requires the creation of a **new project**. Legacy projects will not be migrated.

---

## UI & Pipeline Naming Overhaul

The current overview pipeline labels (e.g., *Edit Entities*, *Edit Relationships*, *Narrative*, *Spatial Editor*, *Finalize*, *Browse Database*) will be replaced.

Forge 3.0 adopts a **dual-label nomenclature strategy**:

* **Left-hand navigation** uses concise, acronym-based phase names for expert efficiency.
* **Overview page** uses full descriptive names paired with acronyms to guide unfamiliar users.
* **Internal code nomenclature remains unchanged** (e.g., `extraction`, `entities`, `relationships`).

### Final Phase Naming (Locked)

**Overview Page (Descriptive):**

* 0 — Extraction (**OSINT**)
* 1 — Entities (**HUMINT**)
* 2 — Relationships (**SIGINT**)
* 3 — Narrative (**SYNTH**)
* 4 — Map (**GEOINT**)
* 5 — Finalize (**Anvil**)

* Project Settings
* View Database
* Browse Files

**Left Navigation (Compact):**

* 0 — OSINT
* 1 — HUMINT
* 2 — SIGINT
* 3 — SYNTH
* 4 — GEOINT
* 5 — ANVIL

This approach fully retires lore-based UI terminology while preserving clarity, expert usability, and onboarding support. The nomenclature change is **purely UI-facing** and introduces no architectural or API impact.

---