# Task: Merge layers profile_key_verticals, profile_line and profile_dist (#40)

## Summary

Merges key verticals and distance markers into `profile_line`, simplifying the group. Applies single-symbol styling (0.5 mm). Updates schema and maps attributes per request.

Closes #40.

## Changes

- Schema: `profile_line` now has fields `id` (string), `symbol`, `txt_label`, and `remarks`.
- Creation: Stop creating `profile_key_verticals` and `profile_dist` layers; route their features into `profile_line`.
- Mapping:
  - Distance markers: `marker_type` → `symbol` (tick), `distance` → `txt_label`, `remarks` = "".
  - Key verticals: `line_type` → `symbol` (key), `segment_name` → `remarks`, `txt_label` = "".
- Styling: Use a single-symbol renderer for `profile_line` set to 0.5 mm width.

### Files

- `qAeroChart/core/layer_manager.py`

## Rationale

- Reduces layer clutter; styling will be provided and can target attributes within a single layer.
- Keeps essential fields requested (`id`, `symbol`, `txt_label`, `remarks`).

## Testing

- Create a profile and verify only these layers exist: `profile_point_symbol`, `profile_carto_label`, `profile_line`, `profile_MOCA`.
- Inspect `profile_line` features:
  - Contains main profile, runway, baseline, merged distance ticks, and key verticals.
  - Fields present: `id`, `symbol`, `txt_label`, `remarks`.
- Confirm line styling: single symbol at 0.5 mm.
- Labels (carto) continue to render with No Symbols.

## Risks & Mitigations

- Low risk; changes are additive and localized to schema/styling and population routing.
- Future styling can be rule-based using `symbol`/`remarks`.

## Checklist

- [x] Branch created from up-to-date `main`: `feature/merge-lines-40`
- [x] Removed separate creation of `profile_key_verticals` and `profile_dist`
- [x] Routed their features into `profile_line` with required mappings
- [x] Updated `profile_line` schema and styling
