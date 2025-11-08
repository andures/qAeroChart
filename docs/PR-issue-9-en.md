# PR: Remove Style Parameters from UI and code (Issue #9)

Issue: Style Parameters removal

## Summary

The Style Parameters panel added clutter and unnecessary complexity. Styling will be handled by predefined QGIS styles users can load and edit later. This change removes the Style Parameters from the UI and cleans related code paths. Axis Max (NM) remains (as requested) and point symbols are always shown.

## Changes

- UI (`ui/profile_creation_dialog_base.ui`)

  - Replaced the “Style Parameters” group with a minimal “Axis” group containing only `Axis max (NM)`.
  - Removed: reverse axis labels, map-unit toggles and widths, MOCA border/point size, view scale hint/enforce, Show ORIGIN marker, Show point symbols.

- Dock widget (`qaerochart_dockwidget.py`)

  - Removed wiring and reads for deleted widgets.
  - Config now only persists `style.vertical_exaggeration` (10×) and `style.axis_max_nm`.

- Layer manager (`core/layer_manager.py`)
  - Simplified `_apply_basic_styles` to fixed millimeter-based defaults; removed map-unit logic.
  - Point symbols are always visible (red, 5 mm).
  - Distance tick, baseline, grid, and key vertical widths use fixed mm widths.
  - Removed reverse-axis label logic; axis labels run 0..AxisMax.
  - Removed ORIGIN marker toggle and view scale enforcement.

## How to test

1. Open the dock; confirm the "Axis" section only shows `Axis max (NM)`.
2. Create a profile and set `Axis max (NM)` larger than the last point distance.
3. Expected:
   - Axis labels: 0..AxisMax along the baseline.
   - Point symbols always visible.
   - No UI for reverse axis, map-unit widths, MOCA border/point size, view-scale, ORIGIN marker.

## Acceptance criteria

- The UI no longer shows Style Parameters except `Axis max (NM)`.
- Generated charts display point symbols by default.
- No usage of removed style options remains in the code path.
- Axis labels increase from 0 to AxisMax.

## Notes

- Future visual refinement should be implemented as QGIS layer styles (.qml) rather than plugin-side widgets/options.
