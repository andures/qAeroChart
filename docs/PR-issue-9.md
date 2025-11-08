# PR: Eliminación de parámetros de estilo en UI y código (Issue #9)

Problema: Style Parameters removal

## Resumen

El panel de parámetros de estilo añadía ruido y complejidad innecesaria. El estilo se gestionará mediante estilos predefinidos de QGIS que el usuario podrá cargar y editar después. Este cambio elimina los parámetros de estilo de la interfaz y limpia la lógica relacionada. Se mantiene `Axis max (NM)` (según pedido) y los símbolos de puntos siempre se muestran.

## Cambios

- UI (`ui/profile_creation_dialog_base.ui`)

  - Se reemplazó el grupo “Style Parameters” por un grupo mínimo “Axis” con solo `Axis max (NM)`.
  - Eliminados: etiquetas de eje invertidas, toggles de unidades de mapa y anchos, borde MOCA/tamaño de punto, pista de escala de vista/forzar, marcador ORIGIN, mostrar símbolos.

- Dock (`qaerochart_dockwidget.py`)

  - Se quitaron conexiones y lecturas de widgets eliminados.
  - La configuración ahora solo persiste `style.vertical_exaggeration` (10×) y `style.axis_max_nm`.

- Administrador de capas (`core/layer_manager.py`)
  - `_apply_basic_styles` simplificado a valores fijos en milímetros; se eliminó la lógica de unidades de mapa.
  - Los símbolos de puntos siempre están visibles (rojo, 5 mm).
  - Ticks, línea base, grilla y verticales clave usan anchos fijos en mm.
  - Se eliminó la lógica de eje invertido; las etiquetas van de 0..AxisMax.
  - Se eliminaron el toggle del marcador ORIGIN y el enforcement de escala de vista.

## Cómo probar

1. Abra el dock y confirme que la sección "Axis" solo muestra `Axis max (NM)`.
2. Cree un perfil y defina `Axis max (NM)` mayor que la última distancia de punto.
3. Esperado:
   - Etiquetas del eje: 0..AxisMax a lo largo de la línea base.
   - Símbolos de puntos visibles siempre.
   - No hay UI para eje invertido, anchos en unidades de mapa, borde MOCA/tamaño de punto, escala de vista, ORIGIN.

## Criterios de aceptación

- La UI ya no muestra parámetros de estilo salvo `Axis max (NM)`.
- Los símbolos de puntos aparecen por defecto.
- No quedan usos de opciones eliminadas en el código.
- Las etiquetas del eje aumentan de 0 a AxisMax.

## Notas

- Las mejoras visuales futuras deben implementarse como estilos de capa de QGIS (.qml), no como opciones del plugin.
