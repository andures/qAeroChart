# PR: Distance markers drawn downward (Issue #8)

Issue: profile_dist the lines are drawn upwards rather than downwards

## Summary

Distance markers (profile distance ticks and grid verticals) were drawn upward from the baseline, which does not match eAIP examples where these are drawn downward. This change flips the direction so markers are drawn downward from the baseline (negative Y), consistent with the expected visual style.

## Changes

- `core/profile_chart_geometry.py`
  - `create_distance_markers`: draw lines downward from baseline by setting the end point to `origin.y() - height` instead of `+ height`.
- Preview behavior (`qaerochart_dockwidget.py`)
  - Continues to use `create_distance_markers`; labels are placed at the end of each tick, now below the baseline.

## How to test

1. Open the profile creation dock and generate a profile with axis up to, e.g., 12 NM.
2. Inspect the distance ticks at each NM along the baseline.
3. Expected: ticks (short) and grid (taller) are drawn downward from the baseline, matching the eAIP reference image.

## Acceptance criteria

- All distance ticks are drawn downward from the baseline across the axis extent.
- Grid verticals also extend downward.
- No regressions to profile line, runway baseline, or OCA/MOCA geometries.

## Notes

- Label positioning for axis/ticks remains below baseline (consistent with downward ticks).
- If future styles require upward ticks, we could add a style toggle `ticks_direction: up|down` (default `down`).
