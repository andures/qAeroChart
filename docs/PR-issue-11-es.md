# PR: Hacer coincidir el orden de símbolos con el árbol de capas (WYSIWYG) – Issue #11

Estado: Abierto → Este PR propone el cambio y documentación.

## Resumen
En algunos proyectos QGIS el dibujo en el lienzo no coincidía con el orden mostrado en el árbol de capas (Layer Panel). El plugin aplicaba un "custom layer order" por código, lo que ocultaba la relación directa WYSIWYG entre el panel y el render.

Este PR elimina el forzado de orden personalizado y desactiva explícitamente cualquier custom layer order activo, de modo que el usuario controle el orden de dibujo simplemente reordenando las capas en el panel.

## Cambios realizados
- Archivo: `qAeroChart/core/layer_manager.py`
  - Eliminado el bloque que construía una lista `preferred` y llamaba a `root.setCustomLayerOrder(new_order)` y `root.setHasCustomLayerOrder(True)`.
  - Añadido un bloque de limpieza que, si existe un orden personalizado activo, ejecuta `root.setHasCustomLayerOrder(False)` para restaurar WYSIWYG.
  - No se tocaron las “estéticas” ni la creación de grupos/capas; solo se quitó la imposición del orden de render.

## Motivo
- QGIS, por defecto, respeta el orden del árbol de capas para dibujar. Forzar un orden externo confunde a usuarios sin experiencia, ya que lo que ven en el árbol no coincide con el resultado.
- Mantener WYSIWYG simplifica soporte y reduce sorpresas.

## Cómo probar
1. Carga el plugin y genera un perfil.
2. Ve al panel "Layer Order" y verifica que la casilla "Control rendering order" esté desactivada (o al menos no se active automáticamente por el plugin).
3. En el árbol de capas, mueve `profile_point_symbol` por encima de `profile_line`.
4. Resultado esperado: en el lienzo los puntos rojos se renderizan por encima de la línea negra. Cambios de orden en el panel se reflejan inmediatamente en el render.

## Criterios de aceptación
- El orden de dibujo del lienzo coincide con el orden del árbol de capas (WYSIWYG) sin intervención adicional.
- No se vuelve a activar el custom layer order al regenerar el perfil.
- No se alteran otras funcionalidades del plugin (estilos, generación de capas, zoom, etc.).

## Notas
- Si en algún proyecto el usuario desea un orden fijo, puede activarlo manualmente desde QGIS (“Control rendering order”) o podríamos ofrecer un toggle en el futuro. Por ahora, el predeterminado es WYSIWYG según lo solicitado.

---

Advertencia: la carpeta `docs/` está ignorada en `.gitignore`, por lo que este archivo no se incluirá en commits a menos que se quite la regla `/docs/` o se haga una excepción específica.
