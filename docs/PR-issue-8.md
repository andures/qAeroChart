# PR: Trazos de distancia hacia abajo (Issue #8)

Problema: profile_dist las líneas se dibujan hacia arriba en lugar de hacia abajo

## Resumen

Los marcadores de distancia (ticks y verticales de grilla) se dibujaban hacia arriba desde la línea base, lo cual no coincide con los ejemplos eAIP donde se dibujan hacia abajo. Este cambio invierte la dirección para que los marcadores se dibujen hacia abajo desde la línea base (Y negativa), acorde al estilo esperado.

## Cambios

- `core/profile_chart_geometry.py`
  - `create_distance_markers`: ahora dibuja las líneas hacia abajo desde la línea base utilizando `origin.y() - height` en lugar de `+ height`.
- Comportamiento del preview (`qaerochart_dockwidget.py`)
  - Continúa usando `create_distance_markers`; las etiquetas quedan en el extremo del tick, ahora debajo de la línea base.

## Cómo probar

1. Abra el dock de creación de perfiles y genere un perfil con eje hasta, por ejemplo, 12 NM.
2. Inspeccione los ticks de distancia en cada NM a lo largo de la línea base.
3. Esperado: los ticks (cortos) y la grilla (más altos) se dibujan hacia abajo desde la línea base, coincidiendo con la referencia eAIP.

## Criterios de aceptación

- Todos los ticks de distancia se dibujan hacia abajo desde la línea base en toda la extensión del eje.
- Las verticales de la grilla también se extienden hacia abajo.
- Sin regresiones en la línea de perfil, la pista en la línea base o las geometrías OCA/MOCA.

## Notas

- El posicionamiento de etiquetas para el eje/ticks se mantiene por debajo de la línea base (consistente con ticks hacia abajo).
- Si en el futuro se requieren ticks hacia arriba, podríamos agregar un toggle de estilo `ticks_direction: up|down` (por defecto `down`).
