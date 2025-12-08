# Task: profile_carto_label layer loaded with No Symbols (#39)

## Summary

Switches the `profile_carto_label` layer to use the "No Symbols" renderer so only labels are shown. This replaces the previous workaround of a transparent point symbol.

Closes #39.

## Changes

- Styling: In `LayerManager._apply_basic_styles`, set renderer for `profile_carto_label` to `QgsNullSymbolRenderer`.
- Fallback: If the null renderer is unavailable, falls back to a fully transparent symbol (defensive).
- Labeling: Existing labeling configuration is preserved and remains enabled.

### Files

- `qAeroChart/core/layer_manager.py`

## Rationale

- The layer is for cartographic text only. Rendering point symbols is unnecessary and can mislead users.
- Using the dedicated No Symbols renderer matches the intent and UI expectation.

## Testing

- Create a profile so layers are generated.
- Select `profile_carto_label` in Layer Styling:
  - The renderer shows "No Symbols".
  - Text labels still display as before (black with white buffer).

## Risks & Mitigations

- Low risk; change is limited to renderer selection for one layer.
- Fallback ensures compatibility if `QgsNullSymbolRenderer` is not available in some environments.

## Checklist

- [x] Branch created from up-to-date `main`: `feature/profile-carto-label-no-symbols-39`
- [x] Applied No Symbols renderer to `profile_carto_label`
- [x] Verified labels appear and points are not drawn
