Based on our project structure, specifically the heavy use of `tkinter.ttk` widgets (Treeviews, Notebooks, Frames) in `pyscrai_forge`, the **`sv-ttk` (Sun Valley)** library is the most streamlined solution. It will "skin" our existing TTK widgets without requiring you to rewrite our entire UI code.

Here is the step-by-step implementation plan for our specific codebase.

### 1. Install the Library

Add `sv-ttk` to our environment:

```bash
pip install sv-ttk

```

### 2. Activate in Main Application

Modify **`pyscrai_forge/src/app/main_app.py`** to apply the theme during initialization. This is the entry point where `tk.Tk()` is created.

```python
# pyscrai_forge/src/app/main_app.py

# ... imports ...
import sv_ttk  # <--- Import this

class ReviewerApp:
    def __init__(self, packet_path: Path | None = None, project_path: Path | None = None):
        self.root = tk.Tk()
        self.root.title("PyScrAI|Forge - Tyler Hamilton v0.9.0")
        self.root.geometry("1400x900")
        
        # ... existing config loading ...
        
        # APPLY THEME HERE
        # Check user config preference, or default to dark
        theme = self.user_config.preferences.theme 
        if theme == "light":
            sv_ttk.set_theme("light")
        else:
            sv_ttk.set_theme("dark") # Default to dark
            
        # ... rest of init ...

```

### 3. Cleanup Hardcoded Colors

A "Dark Mode" requires removing manually set background colors (which are usually light/white) so the theme can handle them.

#### A. Fix the Landing Page Buttons

In **`pyscrai_forge/src/ui/widgets/landing_page.py`**, you are using standard `tk.Button` widgets with specific colors. Standard buttons don't theme well with `sv-ttk`.

* **Recommendation:** Switch to `ttk.Button`. You will lose the specific Green/Blue background colors (unless you write a custom style), but you gain a cohesive professional dark look.

**Change this:**

```python
# pyscrai_forge/src/ui/widgets/landing_page.py

# OLD (Standard tk.Button with hardcoded colors)
new_btn = tk.Button(btn_frame, text="New Project", ..., bg="#219124", ...)

# NEW (Themed ttk.Button)
# Use 'style="Accent.TButton"' provided by sv-ttk for a highlighted primary button
new_btn = ttk.Button(btn_frame, text="New Project", command=self.on_new_project, style="Accent.TButton", width=18)
new_btn.pack(side=tk.LEFT, padx=15)

open_btn = ttk.Button(btn_frame, text="Open Project", command=self.on_open_project, width=18)
open_btn.pack(side=tk.LEFT, padx=15)

```

#### B. Fix Validation Banner & Treeview Colors

In **`pyscrai_forge/src/app/state_manager.py`**, you have hardcoded light backgrounds that will glare in dark mode.

**1. Validation Frame Backgrounds:**
Remove the explicit `bg="#f0f0f0"` arguments. Let the frame inherit the theme background.

```python
# pyscrai_forge/src/app/state_manager.py (~line 115)

# Change this:
self.validation_frame = tk.Frame(self.root, bg="#f0f0f0", height=40)
self.validation_label = tk.Label(self.validation_frame, text="...", bg="#f0f0f0", ...)

# To this (use ttk widgets which auto-theme):
self.validation_frame = ttk.Frame(self.root, height=40) 
self.validation_label = ttk.Label(self.validation_frame, text="...")

```

**2. Treeview Tags (Error/Warning Highlights):**
our error tags use pastel light colors (`#ffcccc`). In dark mode, you need darker colors for the text to remain readable (or to simply not blind the user).

```python
# pyscrai_forge/src/app/state_manager.py (~line 165)

# OLD (Light mode colors)
self.entities_tree.tag_configure("error", background="#ffcccc") 
self.entities_tree.tag_configure("warning", background="#fff4cc")

# NEW (Dark mode friendly)
# Dark Red for error, Dark Yellow/Brown for warning
self.entities_tree.tag_configure("error", background="#550000", foreground="white")
self.entities_tree.tag_configure("warning", background="#554400", foreground="white")

```

### 4. (Optional) Dynamic Toggling

Since you already have a `UserConfig` system, you can add a menu option to toggle themes live.

In **`pyscrai_forge/src/app/main_app.py`**:

```python
def _on_preferences(self) -> None:
    # Simple toggle logic for now
    current_theme = sv_ttk.get_theme()
    new_theme = "light" if current_theme == "dark" else "dark"
    sv_ttk.set_theme(new_theme)
    
    # Save to config
    self.user_config.preferences.theme = new_theme
    self._save_user_config()

```


This is a strong start, but to be truly **comprehensive** for the entire `pyscrai_forge` codebase you shared, we need to address a few more specific files.

our project uses "legacy" styling (manual colors and standard `tk` widgets) in more places than just the Landing Page. If you only follow the previous steps, the **Project Dashboard** and **Database Explorer** will essentially break visually (showing white boxes or unthemed buttons against a dark background).

Here is the **complete checklist** to ensure 100% coverage.

### 1. Fix `project_dashboard.py` (Critical)

This file relies heavily on manually colored frames and buttons for the "Quick Actions" (Import, Edit, Browse).

* **The Issue:** You have a helper method `_create_action_button` that creates a `tk.Frame` and `tk.Button` with hardcoded hex codes (`#4CAF50`, `#2196F3`, etc.).
* **The Fix:** Replace these with `ttk.Button`. `sv-ttk` provides an `Accent.TButton` style for emphasis, but it doesn't support arbitrary colors like "Orange" or "Green" out of the box. You should standardize them to the theme's accent color.

**File:** `pyscrai_forge/src/ui/widgets/project_dashboard.py`

```python
# REMOVE or Comment Out this helper method entirely:
# def _create_action_button(self, parent, text, command, color): ...
# def _darken_color(self, hex_color): ...

# UPDATE _build_ui method:
# Replace the manual button creation calls:
# import_frame = self._create_action_button(action_frame, "📥 Import...", ...)

# WITH standard ttk buttons:
import_btn = ttk.Button(
    action_frame, 
    text="📥 Import Data", 
    command=self.on_import, 
    style="Accent.TButton"  # Highlights this as a primary action
)
import_btn.pack(side=tk.LEFT, padx=15)

edit_btn = ttk.Button(
    action_frame, 
    text="✏️ Edit Components", 
    command=self.on_edit_components
)
edit_btn.pack(side=tk.LEFT, padx=15)

# ... repeat for browse_db ...

```

### 2. Fix `db_explorer.py` (Red Button)

You have a specific "Reset DB" button that is manually styled red. `sv-ttk` actually supports a toggle style that looks like a "danger" button when selected, but for simplicity, just use a standard button or a custom style.

**File:** `pyscrai_forge/src/ui/windows/db_explorer.py`

```python
# OLD
reset_btn = tk.Button(toolbar, text="Reset DB", bg="#d9534f", fg="white", ...)

# NEW (Standard Themed)
reset_btn = ttk.Button(toolbar, text="Reset DB", command=self._reset_database)
# Note: You lose the red color, but it fits the theme. 
# If red is critical, you must define a custom ttk style, but that is advanced.

```

### 3. Updates to `state_manager.py` (Validation Banner)

our previous plan correctly identified this, but ensure you also catch the **Validation Label** background.

**File:** `pyscrai_forge/src/app/state_manager.py`

```python
# OLD
self.validation_frame.config(bg=color)
self.validation_label.config(text=msg, bg=color)

# NEW (Logic Change)
# Instead of setting 'bg', use state-specific styles or just text.
# The simplest dark-mode fix is to change the label TEXT color, not the background frame.
if crit > 0:
    # Error state
    self.validation_label.config(text=msg, foreground="#ff5555") # Bright Red text
elif warn > 0:
    # Warning state
    self.validation_label.config(text=msg, foreground="#ffaa00") # Gold text
else:
    # Valid state
    self.validation_label.config(text=msg, foreground="#55ff55") # Bright Green text

```

### 4. Text Widgets (`tk.Text`)

You use `tk.Text` in `entity_editor.py`, `relationship_editor.py`, and others.

* **Good News:** `sv-ttk` automatically themes standard `tk.Text` widgets to be dark grey with white text.
* **Action:** No code changes needed here *unless* you have manually set `bg="white"` in those files. I checked our files, and you typically initialize them like `tk.Text(self.state_frame, height=15)`, so they will auto-adapt perfectly.

### Summary of the Comprehensive Plan

1. **Install** `sv-ttk`.
2. **Initialize** it in `src/app/main_app.py`.
3. **Refactor Buttons:**
* `src/ui/widgets/landing_page.py` -> Convert `tk.Button` to `ttk.Button`.
* `src/ui/widgets/project_dashboard.py` -> Remove custom frame/button helpers; use `ttk.Button`.
* `src/ui/windows/db_explorer.py` -> Convert Red Reset button to `ttk.Button`.


4. **Refactor Colors:**
* `src/app/state_manager.py` -> Change validation logic to color the **text**, not the background frame.
* `src/app/state_manager.py` -> Update Treeview tags (`error`, `warning`) to use high-contrast text colors suitable for dark mode.



This covers 100% of the UI elements visible in the files you provided.

