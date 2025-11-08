# PR: Perfil ICAO (eAIP) – Preview en vivo, ejes, OCA/MOCA y defaults del ejemplo

Referencia: Issue #1
Fecha: 2025-10-30

## Resumen

Este PR agrega un generador de perfiles distancia–altitud con estética tipo eAIP/ICAO, incluye preview en vivo, escalas visibles, baseline y grilla completas, áreas rayadas controladas por OCA/MOCA, y valores por defecto del ejemplo para verificación visual inmediata. Se priorizó estabilidad (evitando renderers complejos) y visibilidad (capas ordenadas y estilos contrastados).

## Cambios principales

- Estructura de capas en memoria bajo el grupo `MAP 03 - Profile`:
  - `profile_line`, `profile_line_final` (fallback simple) y `profile_line_runway`.
  - `profile_point_symbol` y `profile_carto_label`.
  - `profile_dist` (ticks de distancia), `profile_baseline`, `profile_grid` (grilla vertical completa) y `profile_key_verticals` (FAF/IF/MAPT).
- Estilo y visibilidad (look eAIP):
  - Baseline segmentada (dash con cortes pequeños), caps/joins planos.
  - Grilla vertical clara y dashed; sin etiquetas “N NM” en los ticks.
  - Etiquetas del eje bajo la baseline, con opción de invertir numeración (12 → 0).
  - ORIGIN y símbolos de puntos ocultos por defecto (evita “clutter”).
- OCA/MOCA:
  - Soporte de OCA simple y por segmentos (`oca`, `oca_segments`) con hatch-only.
  - MOCA por segmentos explícitos (`moca_segments`); si hay OCA/MOCA explícita, se omite la MOCA per-point para evitar duplicados.
- Defaults de ejemplo:
  - Eje invertido y `axis_max_nm = 12` por defecto (se puede cambiar en la UI).
  - OCA ejemplo activada por defecto (6.1 → 0.0 NM @ 950 ft), editable/desactivable desde la UI.
- Preview en vivo y auto-zoom:
  - La previsualización incluye baseline y grilla acorde al `axis_max_nm`.
  - Vista normalizada opcional vía `view_scale_hint`.
- Robustez:
  - Renderizador de símbolo único para evitar crashes.
  - Reordenamiento de grupo/capas para asegurar visibilidad; guardas de CRS (advertencia si es geográfico).

## Cambios en la UI (dock)

Se añadieron controles en el formulario embebido (`ui/profile_creation_dialog_base.ui`):

- Eje:
  - “Reverse axis labels (e.g., 12 → 0)” (`checkBox_axis_reverse_labels`).
  - “Axis max (NM)” (`spinBox_axis_max_nm`).
- Visibilidad:
  - “Show ORIGIN marker” (`checkBox_show_origin`).
  - “Show point symbols” (`checkBox_show_point_symbols`).
- OCA:
  - Grupo “Obstacle Coverage (OCA)” con `Enable OCA span` y tres campos:
    - `From (NM)`, `To (NM)`, `OCA height (ft)`.

Estos valores se cargan/guardan en el JSON y se reflejan tanto en el preview como en el render final.

## Formato de configuración (v2.0)

- Claves principales: `origin_point`, `runway`, `profile_points`, `style`, `moca_segments`, `oca`, `oca_segments`.
- Compatibilidad: se mantiene lectura de `reference_point` (v1.0).

Ejemplo de claves nuevas en `style`:

- `axis_reverse_labels: bool`, `axis_max_nm: number`.
- `show_origin: bool`, `show_point_symbols: bool`.

## Cómo probar

1. Abrir el plugin y crear un perfil nuevo.
2. Seleccionar un ORIGIN en el mapa y hacer clic en “Create Profile”.
3. Verificar:
   - Baseline segmentada y grilla vertical completa hasta el “Axis max”.
   - Etiquetas de eje bajo la baseline (por defecto invertidas 12 → 0).
   - ORIGIN y puntos ocultos (activar los toggles si se desea verlos).
   - Área OCA rayada según los valores por defecto (o los que se configuren).

Opcional: Ajustar `Axis max (NM)`, OCA `From/To/ft`, y visibilidad desde la UI; volver a crear/dibujar para comprobar.

## Archivos modificados principales

- `qAeroChart/core/layer_manager.py`
  - Orden/creación de capas, estilos (baseline, grid, dist), labels de eje, OCA/MOCA.
  - Respeta `style.axis_max_nm` en baseline, grid y labels; `style.axis_reverse_labels`.
  - ORIGIN condicional por `style.show_origin`.
- `qAeroChart/qaerochart_dockwidget.py`
  - Construcción de config v2.0 desde la UI; defaults y derivación de `moca_segments`.
  - Preview respetando `axis_max_nm`.
  - Carga/guardado de estilo y OCA en JSON.
- `qAeroChart/utils/json_handler.py`
  - Persistencia de `style`, `moca_segments`, `oca`, `oca_segments`.
- `qAeroChart/ui/profile_creation_dialog_base.ui`
  - Nuevos controles (eje, visibilidad, OCA) y reacomodo de campos.

## Calidad y estabilidad

- Sintaxis Python: OK (validado con análisis estático local).
- Linter/Build: N/A (plugin QGIS); se han minimizado cambios de renderer para evitar crashes.
- Prueba manual recomendada en QGIS 3.x con un proyecto en CRS proyectado (metros). Si el proyecto está en CRS geográfico, se muestra advertencia.

## Notas/Limitaciones

- Aún no hay editor tabular para `oca_segments` en la UI (se puede añadir si es necesario).
- Pendiente: flecha de missed approach y cuadro de transition altitude (si se desea replicar el ejemplo al 100%).

## Siguientes pasos propuestos

- Editor de `oca_segments` (tabla con `from_nm`, `to_nm`, `oca_ft`).
- Estilo/leyenda diferenciados para OCA vs MOCA si se requiere por norma.
- Elementos cartográficos adicionales (missed approach, anotaciones específicas del AIP).

---

Gracias por revisar. Cualquier ajuste fino de valores por defecto (p. ej., OCA(H)/(V)/(M) por tramos exactos del ejemplo) se puede dejar preconfigurado apenas se confirmen las cifras.
