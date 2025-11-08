# PR: ICAO-style Profile (eAIP) – Live preview, axes, OCA/MOCA, and example defaults

Reference: Issue #1  
Date: 2025-10-30

## Summary

This PR adds a distance–altitude profile generator with an eAIP/ICAO look. It includes a live preview, visible scales, full baseline and grid, hatched areas controlled by OCA/MOCA, and example defaults for immediate visual verification. We prioritized stability (avoiding complex renderers) and visibility (ordered layers and high-contrast styles).

## Main changes

- In-memory layer structure under group `MAP 03 - Profile`:
  - `profile_line`, `profile_line_final` (simple fallback), and `profile_line_runway`.
  - `profile_point_symbol` and `profile_carto_label`.
  - `profile_dist` (distance ticks), `profile_baseline`, `profile_grid` (full vertical grid), and `profile_key_verticals` (FAF/IF/MAPT).
- Style and visibility (eAIP look):
  - Segmented/dashed baseline with small cuts; flat caps/joins.
  - Clean dashed vertical grid; no “N NM” labels on ticks.
  - Axis labels under the baseline with optional reverse numbering (12 → 0).
  - ORIGIN and point symbols hidden by default (reduces clutter).
- OCA/MOCA:
  - Support for single-span OCA and segmented OCA (`oca`, `oca_segments`) with hatch-only styling.
  - Explicit MOCA segments (`moca_segments`); when OCA/MOCA explicit coverage is provided, per-point MOCA is skipped to avoid duplicates.
- Example defaults:
  - Axis reversed and `axis_max_nm = 12` by default (configurable in the UI).
  - Example OCA enabled by default (6.1 → 0.0 NM @ 950 ft), editable or switchable off in the UI.
- Live preview and auto-zoom:
  - Preview includes baseline and grid according to `axis_max_nm`.
  - Optional view normalization via `view_scale_hint`.
- Robustness:
  - Single symbol renderer to avoid crashes.
  - Group/layer reordering to ensure visibility; CRS guards (warning if geographic CRS).

## UI changes (dock)

New controls were added to the embedded form (`ui/profile_creation_dialog_base.ui`):

- Axis:
  - “Reverse axis labels (e.g., 12 → 0)” (`checkBox_axis_reverse_labels`).
  - “Axis max (NM)” (`spinBox_axis_max_nm`).
- Visibility:
  - “Show ORIGIN marker” (`checkBox_show_origin`).
  - “Show point symbols” (`checkBox_show_point_symbols`).
- OCA:
  - “Obstacle Coverage (OCA)” group with `Enable OCA span` and three fields:
    - `From (NM)`, `To (NM)`, `OCA height (ft)`.

These values are saved to/loaded from JSON and are reflected in both the live preview and the final render.

## Configuration format (v2.0)

- Main keys: `origin_point`, `runway`, `profile_points`, `style`, `moca_segments`, `oca`, `oca_segments`.
- Compatibility: still reads `reference_point` (v1.0).

New `style` keys examples:

- `axis_reverse_labels: bool`, `axis_max_nm: number`.
- `show_origin: bool`, `show_point_symbols: bool`.

## How to test

1. Open the plugin and create a new profile.
2. Select an ORIGIN on the map and click “Create Profile”.
3. Verify:
   - Segmented baseline and full vertical grid up to “Axis max”.
   - Axis labels under the baseline (reversed 12 → 0 by default).
   - ORIGIN and points are hidden (use toggles to show them if desired).
   - OCA hatched area according to defaults (or your configured values).

Optional: Adjust `Axis max (NM)`, OCA `From/To/ft`, and visibility from the UI; re-create/redraw to confirm.

## Key modified files

- `qAeroChart/core/layer_manager.py`
  - Layer order/creation, styles (baseline, grid, ticks), axis labels, OCA/MOCA.
  - Respects `style.axis_max_nm` for baseline, grid, and labels; `style.axis_reverse_labels`.
  - ORIGIN conditional via `style.show_origin`.
- `qAeroChart/qaerochart_dockwidget.py`
  - Build v2.0 config from UI; defaults and `moca_segments` derivation.
  - Preview honoring `axis_max_nm`.
  - Load/save of style and OCA in JSON.
- `qAeroChart/utils/json_handler.py`
  - Persists `style`, `moca_segments`, `oca`, `oca_segments`.
- `qAeroChart/ui/profile_creation_dialog_base.ui`
  - New controls (axis, visibility, OCA) and field reflow.

## Quality and stability

- Python syntax: OK (validated with local static analysis).
- Linter/Build: N/A (QGIS plugin); renderer swaps minimized to avoid crashes.
- Manual test recommended in QGIS 3.x with a projected CRS (meters). If the project uses a geographic CRS, a warning is shown.

## Notes/Limitations

- No UI table yet for `oca_segments` (can be added if needed).
- Pending: missed approach arrow and transition altitude box (if exact eAIP replication is required).

## Proposed next steps

- UI editor for `oca_segments` (table with `from_nm`, `to_nm`, `oca_ft`).
- Optional distinct styling/legend for OCA vs MOCA if required by spec.
- Additional carto elements (missed approach, AIP-specific annotations).

---

Thanks for reviewing. If you can share exact example values for OCA(H)/(V)/(M) by segments, we can preconfigure them as defaults right away.
