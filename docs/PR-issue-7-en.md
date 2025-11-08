# PR: Vertical scale 10× exaggeration (Issue #7)

Issue: Vertical Scale is not 10× exaggerated

## Summary

Implemented a 10× vertical exaggeration for all altitude-dependent geometry so that a 2,000 ft input measures as ~20,000 ft on the map (when measuring vertical separation). This matches charting practice and the client’s expectation/screenshots.

## Changes

- `core/profile_chart_geometry.py`
  - Added constructor parameter `vertical_exaggeration` (default 10.0) and instance scales.
  - Applied the exaggeration to all Y computations: profile points, MOCA/OCA polygons, and distance markers.
  - Kept horizontal scale 1:1.
- `core/layer_manager.py`
  - Reads `style.vertical_exaggeration` (default 10.0) and passes it to `ProfileChartGeometry`.
  - Adjusted UI-driven visual offsets to stay readable under exaggeration:
    - Slope label offset: `+80 ft` → `+80/VE ft` (visual constant).
    - Axis labels below baseline: `-60 ft` → `-60/VE ft`.
  - Key verticals height: `3000 m` → `3000/VE m` (so they don’t blow up the extent).
  - Tick lines: `200 m` → `200/VE m` (visual constant ~200 m after VE).
  - Full gridlines: `1500 m` → `1500/VE m` (shorter to reduce clutter on the basemap).
- `qaerochart_dockwidget.py`
  - Live preview uses the same 10× exaggeration and preserves tick/grid visual sizes with the same division by VE.
- `qaerochart_dockwidget.py` (build config)
  - Persists `style.vertical_exaggeration = 10.0` in the config.

## Rationale

- The profile should be legible and match ICAO/eAIP presentation. Exaggerating Y by 10× ensures the slope and altitude changes are visible, and measurement over Y reflects 10×.

## How to test

1. Load the attached config: `profile_07_20251105_201033.json` (or create a similar one).
2. Generate the profile. With the QGIS measure tool set to feet, measure from baseline (Y=0) up to a point with 2,000 ft input elevation.
3. Expected: measurement ≈ 20,000 ft (10× the input).
4. Verify that ticks, gridlines, and labels look proportionate (not exploding the extent).

## Acceptance criteria

- Measured vertical separation reflects 10× of the user-entered altitude (2,000 → 20,000 ft, etc.).
- Profile, MOCA/OCA, and runway render correctly alongside the new vertical exaggeration.
- No excessive canvas extent growth; auto-zoom remains practical.

## Notes / Follow-ups (optional)

- Expose `vertical_exaggeration` as a UI control (default 10). Allow 5×, 10×, 20× presets.
- Align slope label rotation to the exaggerated line angle (today it reflects real gradient; we can add a toggle).
- Consider computing grid height from data (max content + margin) instead of a fixed 1500 m baseline for dynamic charts.
