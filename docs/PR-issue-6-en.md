# PR: Fix runway drawing placement (Issue #6)

Issue: Runway drawing not in the correct location

## Summary

The profile’s origin represents the THR (start of runway). The runway segment must appear on the opposite side of the profile axis so that distances 0→N NM extend away from the runway. Also, the runway must start exactly at the 0 NM vertical and lie on the baseline (Y=0).

This PR updates the geometry builder to draw the runway from (origin − length) → origin at Y=0, eliminating the offset and aligning the runway end with the 0 NM gridline.

## Changes

- `core/profile_chart_geometry.py`
  - `create_runway_line(length_m, _tch_m_unused=0.0)` now:
    - Draws the runway entirely to the left of the origin (negative X) from origin−length to origin.
    - Places the runway on the baseline (Y=0). TCH is no longer used for vertical placement of the runway.
    - Keeps the second parameter for signature compatibility (ignored).

## Rationale

- Matches expected ICAO/eAIP look: profile distances increase to the right, runway lies to the left, ending exactly at 0 NM.
- Fixes the visual mismatch shown in the client’s images (vertex alignment at 0 NM and opposite-side requirement).

## How to test

1. Open the plugin and generate a profile with a non-zero runway length.
2. Verify the runway thick black line:
   - Lies on the baseline (Y=0).
   - Extends to the left of 0 NM.
   - Ends exactly at the 0 NM vertical gridline.
3. Verify that the profile line and grid still render as before.

## Acceptance criteria

- Runway drawn from origin−length to origin at Y=0.
- No offset at 0 NM; runway end coincides with the 0 NM vertical.
- No regressions in profile/grid/hatching rendering.

## Beyond the ask (optional follow-ups)

- Toggle for runway side: allow left/right placement (default left). Useful for special-case procedures.
- Runway as filled rectangle option (polygon) for closer eAIP fidelity.
- 0 NM anchor label (e.g., “THR RWY 07”) and tiny tick enhancement.
- Form validation: warn if runway length is 0 or origin not set.
