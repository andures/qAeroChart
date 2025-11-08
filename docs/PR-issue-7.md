# PR: Escala vertical exagerada 10× (Issue #7)

Problema: La escala vertical no está exagerada 10×

## Resumen

Se implementó una exageración vertical de 10× para toda la geometría que depende de altitud, de modo que un valor de 2,000 ft se mida como ~20,000 ft en el mapa (al medir una separación vertical). Esto coincide con la práctica de cartografía y con lo mostrado por el cliente.

## Cambios

- `core/profile_chart_geometry.py`
  - Se añadió parámetro de constructor `vertical_exaggeration` (10.0 por defecto) y escalas por instancia.
  - Se aplica la exageración a todos los cálculos en Y: puntos del perfil, polígonos MOCA/OCA y marcadores de distancia.
  - La escala horizontal se mantiene 1:1.
- `core/layer_manager.py`
  - Lee `style.vertical_exaggeration` (10.0 por defecto) y lo pasa a `ProfileChartGeometry`.
  - Ajustes para mantener legibilidad con VE:
    - Offset de etiqueta de pendiente: `+80 ft` → `+80/VE ft`.
    - Etiquetas del eje bajo la línea base: `-60 ft` → `-60/VE ft`.
    - Altura de verticales clave: `3000 m` → `3000/VE m`.
    - Ticks: `200 m` → `200/VE m`.
    - Grilla completa: `3000 m` → `3000/VE m`.
- `qaerochart_dockwidget.py`
  - El preview usa también 10× y conserva tamaños visuales de tick/grilla dividiendo por VE.
- `qaerochart_dockwidget.py` (construcción de config)
  - Persiste `style.vertical_exaggeration = 10.0` en la configuración.

## Razonamiento

- El perfil debe ser legible y acorde a eAIP. Exagerar Y 10× hace visible la pendiente/relieves y la medición vertical refleja 10×.

## Cómo probar

1. Cargar la config adjunta: `profile_07_20251105_201033.json` (o similar).
2. Generar el perfil. Con la herramienta de medición de QGIS en pies, medir desde la línea base (Y=0) hasta un punto con 2,000 ft de entrada.
3. Esperado: medición ≈ 20,000 ft (10× el valor de entrada).
4. Verificar que ticks, grilla y etiquetas se vean proporcionales (sin explotar la extensión del lienzo).

## Criterios de aceptación

- La separación vertical medida refleja 10× del valor ingresado (2,000 → 20,000 ft, etc.).
- El perfil, MOCA/OCA y pista se renderizan correctamente con la nueva exageración vertical.
- La extensión del canvas no crece en exceso; el auto-zoom sigue siendo práctico.

## Notas / Seguimiento (opcional)

- Exponer `vertical_exaggeration` en la UI (por defecto 10) con presets 5×, 10×, 20×.
- Alinear la rotación de la etiqueta de pendiente al ángulo exagerado (hoy refleja la pendiente real; se puede agregar un toggle).
- Considerar altura de grilla derivada de datos (máximo contenido + margen) en lugar de 3000 m fijos.
