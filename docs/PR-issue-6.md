# PR: Corrección de ubicación de la pista (Issue #6)

Problema: La pista no se dibuja en la ubicación correcta

## Resumen

El origen del perfil representa el THR (umbral de pista). La pista debe dibujarse en el lado opuesto del eje del perfil para que las distancias 0→N NM se extiendan alejándose de la pista. Además, la pista debe iniciar exactamente en la vertical de 0 NM y estar sobre la línea base (Y=0).

Este PR actualiza el generador de geometrías para dibujar la pista desde (origen − longitud) → origen en Y=0, eliminando el desfase y alineando el extremo de la pista con la línea vertical de 0 NM.

## Cambios

- `core/profile_chart_geometry.py`
  - `create_runway_line(length_m, _tch_m_unused=0.0)` ahora:
    - Dibuja la pista completamente a la izquierda del origen (X negativo), desde origen−longitud hasta el origen.
    - Coloca la pista sobre la línea base (Y=0). TCH ya no se usa para ubicar verticalmente la pista.
    - Mantiene el segundo parámetro por compatibilidad de firma (ignorado).

## Razonamiento

- Coincide con la estética ICAO/eAIP esperada: las distancias del perfil crecen hacia la derecha, mientras la pista queda a la izquierda y termina exactamente en 0 NM.
- Corrige el desajuste visual mostrado en las imágenes del cliente (alineación del vértice en 0 NM y requisito de “lado opuesto”).

## Cómo probar

1. Abrir el plugin y generar un perfil con longitud de pista mayor a 0.
2. Verificar que la línea gruesa de pista:
   - Está sobre la línea base (Y=0).
   - Se extiende hacia la izquierda de 0 NM.
   - Termina exactamente en la vertical de 0 NM.
3. Verificar que la línea del perfil y la grilla se renderizan como antes.

## Criterios de aceptación

- Pista dibujada desde origen−longitud hasta el origen en Y=0.
- Sin desfase en 0 NM; el extremo de la pista coincide con la vertical de 0 NM.
- Sin regresiones en el render del perfil/grilla/hatched.

## Más allá del pedido (seguimiento opcional)

- Conmutador para el lado de la pista: permitir izquierda/derecha (por defecto izquierda).
- Opción de pista como rectángulo relleno (polígono) para mayor fidelidad eAIP.
- Etiqueta de anclaje en 0 NM (p.ej., “THR RWY 07”) y pequeño tick de realce.
- Validación en el formulario: avisar si la pista es 0 o no se definió origen.
