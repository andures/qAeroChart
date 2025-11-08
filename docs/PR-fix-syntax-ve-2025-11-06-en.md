# Fix: stabilize code (indentation/syntax) after VE & runway updates

- Issue: Stabilization pass after VE=10× and runway baseline/origin changes
- Date: 2025-11-06
- Author: andures

## Summary

After adding 10× vertical exaggeration and updating runway placement (Issue #7/#6), static checks reported indentation/syntax errors. This PR fixes all scope/indentation regressions and ensures consistent scaling in helper methods.

## Changes

- Corrected mis-indented lines causing `unexpected indentation` and `return can be used only within a function` in:
  - `core/profile_chart_geometry.py`: `calculate_profile_point`, `create_runway_line`, `create_distance_markers`, `create_vertical_reference_line`, `create_oca_box`.
  - `qaerochart_dockwidget.py`: `_build_config_from_form` variable section.
- Consistency: `create_vertical_reference_line` now applies horizontal scale to X and vertical exaggeration to height.

## How to test

1. Load the plugin inside a QGIS 3.x environment.
2. Open the dock, use default example data, pick an origin point.
3. Generate a profile and confirm:
   - No Python errors in the logs (dock + console).
   - Runway line sits on baseline (Y=0), left of origin, ending exactly at 0 NM.
   - VE=10× visually: a 2,000 ft point appears at ~20,000 ft vertical (exaggerated display).
   - Tick heights look ~200 m and grid ~3,000 m visually (normalized for VE).

## Acceptance criteria

- [ ] Plugin loads without syntax/indentation errors.
- [ ] Rendering respects runway baseline/origin constraints (Issue #6).
- [ ] Vertical exaggeration 10× applied consistently (Issue #7) and preview parity maintained.
- [ ] No regressions: OCA/MOCA geometry renders correctly; hatching precedence intact.

## Risks and mitigations

- QGIS imports may be reported unresolved by non-QGIS linters. Mitigated by validating inside QGIS.

## Documentation updates

- PULL_REQUEST_TEMPLATE enforces docs in `docs/` for each PR.
- This document serves as the PR doc for the stabilization fix.
