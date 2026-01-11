# NavigationRail Height Error - Documentation & Solutions

## Error Description

**Error Message (displayed in red box on left side of UI):**
```
Error displaying NavigationRail: height is unbounded. Either set a fixed "height" or nest 
NavigationRail inside expanded control or control with a fixed height.
```

**Location:** forge/presentation/layouts/shell.py in the `build_shell()` function  
**Severity:** Non-critical (app runs but displays error overlay)

---

## Root Cause Analysis

In Flet framework, `NavigationRail` is a Material Design navigation component that requires explicit height constraints. The error occurs when:

1. NavigationRail is wrapped in containers without proper height context
2. The parent Row/Column doesn't have `expand=True`
3. Multiple nesting levels prevent height propagation

**Current code (lines ~160 in shell.py):**
```python
ft.Container(width=88, expand=False, content=ft.Column([nav_rail], expand=True))
```

This fails because:
- Container has fixed width (88) but no explicit height
- Column.expand=True doesn't work without parent context
- NavigationRail has no height property set

---

## Fixes Attempted

### Fix 1: Wrap in Column with expand=True
**Result:** ❌ Failed - Column needs parent Row context

### Fix 2: Add expand=True to parent Row  
**Result:** ⚠️ Partial - Error persists due to over-nesting

---

## Solution (Per Flet Official Documentation)

**Source:** https://flet.dev/docs/controls/navigationrail (official example)

The correct pattern is:
```python
ft.Row([
    ft.NavigationRail(...),  # Direct placement, no wrapping
    ft.VerticalDivider(),
    ft.Column([...], expand=True)
], expand=True)  # Critical: Row must expand
```

**Key requirements:**
1. Place NavigationRail directly in Row (not in Container)
2. Row must have `expand=True`
3. Parent Container must have `expand=True`
4. NavigationRail.min_width provides width constraint

---

## Implementation

**File:** shell.py (lines 152-165)

**Change this:**
```python
ft.Container(width=88, expand=False, content=ft.Column([nav_rail], expand=True))
```

**To this:**
```python
nav_rail
```

Remove the unnecessary Container/Column wrapper and place NavigationRail directly in the Row.

**Test:** `python3 forge/main.py`  
**Expected:** Error box disappears, full-height navigation sidebar displays

---

## References

- Flet NavigationRail: https://flet.dev/docs/controls/navigationrail
- Official Example: https://github.com/flet-dev/examples/blob/main/python/controls/navigation/navigation-rail/nav-rail-test.py
- Flet Layout Constraints: https://flet.dev/docs/guides/layouts/constraints

---

## Status

- ✅ App runs successfully despite error
- ⚠️ Error overlay displayed but non-functional
- 🔧 Solution identified but requires code change
- ⏳ Implementation pending
```

To apply this fix, you'll need to edit [forge/presentation/layouts/shell.py](forge/presentation/layouts/shell.py#L160) and simplify the NavigationRail container setup.To apply this fix, you'll need to edit [forge/presentation/layouts/shell.py](forge/presentation/layouts/shell.py#L160) and simplify the NavigationRail container setup.