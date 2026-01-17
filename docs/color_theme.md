# PyScrAI Forge - Color Theme Documentation

## Overview
This document defines the standardized color palette for PyScrAI Forge UI components to ensure consistent visual hierarchy and improved readability.

## Core Color Palette

### Primary Colors
- **Primary Accent**: `#48b0f7` (Cyan Blue) - Used for primary actions, icons, and highlights
- **Secondary Accent**: `#4ECDC4` (Teal) - Used for secondary highlights and success states

### Text Colors
Following a clear hierarchy for optimal readability:

| Level | Hex Code | Use Case | CSS Color | Description |
|-------|----------|----------|-----------|-------------|
| **Primary Text** | `#E8F1F8` | Main headings, important labels | Near White | Highest contrast for primary content |
| **Secondary Text** | `#B8C5D0` | Subheadings, button text, normal labels | Light Gray-Blue | Standard readable text |
| **Tertiary Text** | `#8A9BA8` | Placeholders, hints, disabled states | Muted Gray | Less prominent content |

### Status & Semantic Colors
- **Info**: `#48b0f7` (Cyan) - Information messages
- **Success**: `#4ECDC4` (Teal) - Success confirmations
- **Warning**: `#FFD93D` (Yellow) - Warning alerts
- **Error**: `#FF6B6B` (Red) - Error messages

### Background Colors
- **Base Background**: `#000000` (Pure Black)
- **Canvas Gradient**: `#0d1528` → `#0a0f1c` → `#060a12` (Dark Blue to Black gradient)
- **Navigation**: `#0a0d1f` (Dark Blue)
- **Card/Container**: `rgba(255,255,255,0.025)` (Subtle white overlay)
- **Panel**: `rgba(255,255,255,0.04)` (Slightly brighter overlay)

### Border & Divider Colors
- **Subtle Border**: `rgba(255,255,255,0.06)` - Minimal separation
- **Normal Border**: `rgba(255,255,255,0.1)` - Standard borders
- **Divider**: `rgba(255,255,255,0.12)` - Section dividers

## Component-Specific Usage

### Buttons
```python
ft.OutlinedButton(
    "Button Text",
    icon=ft.Icons.ICON_NAME,
    icon_color="#B8C5D0",  # Secondary text color
    style=ft.ButtonStyle(
        color="#E8F1F8",  # Primary text color
    ),
)
```

### Text Elements
```python
# Primary heading
ft.Text("Heading", size=22, weight=ft.FontWeight.W_700, color="#E8F1F8")

# Secondary heading
ft.Text("Subheading", size=16, weight=ft.FontWeight.W_600, color="#B8C5D0")

# Body text / labels
ft.Text("Label", size=14, color="#B8C5D0")

# Hints / placeholders
ft.Text("Placeholder", size=12, color="#8A9BA8", italic=True)
```

### Icons
```python
# Primary icons (active)
ft.Icon(ft.Icons.ICON_NAME, color="#48b0f7", size=26)

# Secondary icons
ft.Icon(ft.Icons.ICON_NAME, color="#B8C5D0", size=18)

# Muted icons
ft.Icon(ft.Icons.ICON_NAME, color="#8A9BA8", size=16)
```

### Containers & Cards
```python
ft.Container(
    bgcolor="rgba(255,255,255,0.025)",
    border_radius=12,
    border=ft.border.all(1, "rgba(255,255,255,0.06)"),
    padding=14,
)
```

### Stat Cards
```python
ft.Container(
    bgcolor="rgba(255,255,255,0.025)",
    padding=ft.padding.symmetric(horizontal=14, vertical=12),
    border_radius=8,
    border=ft.border.all(1, "rgba(255,255,255,0.1)"),
    content=ft.Column([
        ft.Row([
            ft.Icon(icon, color="#48b0f7", size=16),
            ft.Text(value, size=20, weight=ft.FontWeight.W_700, color="#E8F1F8"),
        ]),
        ft.Text(label, size=11, color="#8A9BA8", weight=ft.FontWeight.W_500)
    ])
)
```

### Dividers
```python
# Standard divider
ft.Divider(color="rgba(255, 255, 255, 0.12)", height=1)

# Vertical divider
ft.VerticalDivider(width=1, color="rgba(255,255,255,0.12)")
```

## Accessibility Notes

1. **Contrast Ratios**:
   - Primary text (#E8F1F8) on dark backgrounds: ~15:1 ratio
   - Secondary text (#B8C5D0) on dark backgrounds: ~10:1 ratio
   - Tertiary text (#8A9BA8) on dark backgrounds: ~6:1 ratio

2. **Color Blindness Considerations**:
   - Status colors use both color and iconography
   - Interactive elements have sufficient contrast regardless of color perception

3. **Visual Hierarchy**:
   - 3-level text hierarchy prevents visual clutter
   - Icon colors reinforce interactive elements
   - Consistent spacing complements color hierarchy

## Migration Guide

When updating existing components:

1. **Replace** `ft.Colors.WHITE` → `#E8F1F8` (primary text)
2. **Replace** `ft.Colors.WHITE70` → `#B8C5D0` (secondary text)
3. **Replace** `ft.Colors.WHITE54` → `#8A9BA8` (tertiary text)
4. **Replace** `ft.Colors.CYAN_300` → `#48b0f7` (primary accent)
5. **Update** divider colors to `rgba(255, 255, 255, 0.12)`
6. **Update** borders to `rgba(255,255,255,0.06)` or `rgba(255,255,255,0.1)`

## Testing Checklist

- [ ] Text is readable in all lighting conditions
- [ ] Interactive elements are clearly distinguishable
- [ ] Status messages use appropriate semantic colors
- [ ] Buttons have consistent styling across views
- [ ] Hover states provide visual feedback
- [ ] Focus indicators meet accessibility standards

---

**Last Updated**: January 16, 2026  
**Version**: 1.0
