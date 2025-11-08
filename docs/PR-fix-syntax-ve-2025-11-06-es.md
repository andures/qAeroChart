# Fix: estabilizar código (indentación/sintaxis) tras VE y pista

- Issue: Pase de estabilización después de la exageración vertical 10× y el ajuste de pista/origen
- Fecha: 2025-11-06
- Autor: andures

## Resumen

Tras implementar la exageración vertical (10×) y corregir la ubicación de la pista (Issue #7/#6), los chequeos estáticos reportaron errores de indentación/sintaxis. Este PR corrige todas las regresiones de ámbito/indentación y asegura un escalado coherente en los métodos auxiliares.

## Cambios

- Correcciones de líneas mal indentadas que causaban `unexpected indentation` y `return can be used only within a function` en:
  - `core/profile_chart_geometry.py`: `calculate_profile_point`, `create_runway_line`, `create_distance_markers`, `create_vertical_reference_line`, `create_oca_box`.
  - `qaerochart_dockwidget.py`: sección de variables en `_build_config_from_form`.
- Consistencia: `create_vertical_reference_line` ahora aplica escala horizontal al X y exageración vertical a la altura.

## Cómo probar

1. Cargar el plugin en un entorno QGIS 3.x.
2. Abrir el dock, usar los datos ejemplo por defecto y elegir un origen.
3. Generar el perfil y confirmar:
   - Sin errores de Python en logs (dock + consola).
   - La pista se dibuja en la línea base (Y=0), a la izquierda del origen, terminando exactamente en 0 NM.
   - VE=10×: un punto de 2,000 ft se ve a ~20,000 ft verticalmente (visual exagerado).
   - Altura de ticks ~200 m y de la grilla ~3,000 m de forma visual (normalizados por VE).

## Criterios de aceptación

- [ ] El plugin carga sin errores de sintaxis/indentación.
- [ ] El render respeta la pista en la base y alineación con 0 NM (Issue #6).
- [ ] La exageración vertical 10× se aplica consistentemente (Issue #7) y la vista previa coincide.
- [ ] Sin regresiones: OCA/MOCA dibujan correctamente; la precedencia de sombreado se mantiene.

## Riesgos y mitigaciones

- Los linters fuera de QGIS pueden marcar imports de QGIS no resueltos. Mitigado validando dentro de QGIS.

## Actualizaciones de documentación

- La plantilla de PR (PULL_REQUEST_TEMPLATE) exige documentos en `docs/` por PR.
- Este documento sirve como PR para la estabilización.
