# Notas de Investigación - PyQGIS 3.40

Documento de referencia técnica para el desarrollo del plugin qAeroChart, basado en la documentación oficial de QGIS 3.40.

## 1. Map Canvas Tools y User Interaction

### 1.1 QgsMapTool - Herramienta Base

Para crear herramientas personalizadas de interacción con el mapa canvas:

```python
from qgis.gui import QgsMapToolEmitPoint

class CustomMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)

    def canvasPressEvent(self, e):
        # Obtener coordenadas del click
        self.startPoint = self.toMapCoordinates(e.pos())

    def canvasReleaseEvent(self, e):
        # Acción al soltar el botón
        pass

    def canvasMoveEvent(self, e):
        # Actualizar mientras se mueve el cursor
        self.endPoint = self.toMapCoordinates(e.pos())

    def deactivate(self):
        QgsMapTool.deactivate(self)
        self.deactivated.emit()
```

**Métodos principales:**

- `canvasPressEvent(e)` - Click inicial del ratón
- `canvasReleaseEvent(e)` - Al soltar el botón
- `canvasMoveEvent(e)` - Movimiento del cursor
- `toMapCoordinates(e.pos())` - Convierte posición de pantalla a coordenadas del mapa
- `deactivate()` - Limpieza al desactivar la herramienta

### 1.2 QgsRubberBand - Feedback Visual

Para mostrar elementos temporales en el canvas:

```python
from qgis.gui import QgsRubberBand
from qgis.core import QgsWkbTypes

# Para líneas
r = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
points = [QgsPoint(-100, 45), QgsPoint(10, 60), QgsPoint(120, 45)]
r.setToGeometry(QgsGeometry.fromPolyline(points), None)

# Para puntos (usar QgsVertexMarker es mejor)
m = QgsVertexMarker(canvas)
m.setCenter(QgsPointXY(10, 40))
m.setColor(QColor(0, 255, 0))
m.setIconSize(5)
m.setIconType(QgsVertexMarker.ICON_CROSS)  # o ICON_BOX, ICON_X
m.setPenWidth(3)

# Personalización
r.setColor(QColor(0, 0, 255))
r.setWidth(3)

# Ocultar/mostrar
r.hide()
r.show()

# Eliminar
canvas.scene().removeItem(r)
```

**Tipos de geometría:**

- `QgsWkbTypes.PointGeometry`
- `QgsWkbTypes.LineGeometry`
- `QgsWkbTypes.PolygonGeometry`

### 1.3 Activar Map Tool

```python
# Desde el plugin
canvas = iface.mapCanvas()
myTool = CustomMapTool(canvas)
canvas.setMapTool(myTool)

# Asociar con QAction (checkable)
self.actionMyTool = QAction("My Tool", self)
self.actionMyTool.setCheckable(True)
self.actionMyTool.triggered.connect(self.activateMyTool)

self.toolMyTool = CustomMapTool(self.canvas)
self.toolMyTool.setAction(self.actionMyTool)

def activateMyTool(self):
    self.canvas.setMapTool(self.toolMyTool)
```

## 2. Memory Layers (Vector Layers)

### 2.1 Crear Memory Layer con Campos

```python
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsPointXY
from qgis.PyQt.QtCore import QMetaType

# Crear layer con especificación completa en URI
vl = QgsVectorLayer(
    "Point?crs=epsg:4326&field=id:integer&field=name:string(20)&index=yes",
    "temporary_points",
    "memory"
)

# O crear layer y agregar campos después
vl = QgsVectorLayer("Point", "temporary_points", "memory")
pr = vl.dataProvider()

# Agregar campos
pr.addAttributes([
    QgsField("name", QMetaType.Type.QString),
    QgsField("age", QMetaType.Type.Int),
    QgsField("size", QMetaType.Type.Double),
    QgsField("birthday", QMetaType.Type.QDateTime)
])
vl.updateFields()  # IMPORTANTE: actualizar campos

# Agregar features
fet = QgsFeature()
fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(10, 10)))
fet.setAttributes(["Johnny", 2, 0.3, QDateTime.fromString("2000-01-01T12:00:00", Qt.DateFormat.ISODate)])
pr.addFeatures([fet])

# Actualizar extent
vl.updateExtents()

# Agregar al proyecto
QgsProject.instance().addMapLayer(vl)
```

**Tipos de geometría en URI:**

- `"Point"` - Puntos simples
- `"LineString"` - Líneas
- `"Polygon"` - Polígonos
- `"MultiPoint"`, `"MultiLineString"`, `"MultiPolygon"` - Multi-geometrías
- `"None"` - Sin geometría (solo tabla de atributos)

**Opciones del URI:**

- `crs=epsg:4326` - Sistema de coordenadas
- `field=name:type(length,precision)` - Definir campos
- `index=yes` - Habilitar índice espacial

**Tipos de campos (QMetaType.Type):**

- `QString` - Texto
- `Int` - Entero
- `Double` - Decimal
- `Bool` - Booleano
- `QDateTime` - Fecha/hora
- `QDate` - Solo fecha

### 2.2 Modificar Vector Layers

```python
# Verificar capacidades
caps = layer.dataProvider().capabilities()
if caps & QgsVectorDataProvider.AddFeatures:
    # Agregar features
    feat = QgsFeature(layer.fields())
    feat.setAttributes([0, 'hello'])
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(123, 456)))
    (res, outFeats) = layer.dataProvider().addFeatures([feat])

# Eliminar features
if caps & QgsVectorDataProvider.DeleteFeatures:
    res = layer.dataProvider().deleteFeatures([5, 10])

# Modificar atributos
if caps & QgsVectorDataProvider.ChangeAttributeValues:
    attrs = {0: "hello", 1: 123}
    layer.dataProvider().changeAttributeValues({fid: attrs})

# Modificar geometría
if caps & QgsVectorDataProvider.ChangeGeometries:
    geom = QgsGeometry.fromPointXY(QgsPointXY(111, 222))
    layer.dataProvider().changeGeometryValues({fid: geom})
```

### 2.3 Edición con Buffer (para Undo/Redo)

```python
# Iniciar edición
layer.startEditing()

# Usar context manager (recomendado)
from qgis.core.additions.edit import edit

with edit(layer):
    feat = next(layer.getFeatures())
    feat[0] = 5
    layer.updateFeature(feat)
    # Commit automático al salir del context
    # Rollback automático si hay excepción

# O manualmente
layer.beginEditCommand("Feature triangulation")
# ... hacer cambios ...
if problem_occurred:
    layer.destroyEditCommand()
else:
    layer.endEditCommand()

layer.commitChanges()  # o layer.rollBack()
```

### 2.4 Iterar sobre Features

```python
# Todas las features
for feature in layer.getFeatures():
    print(f"ID: {feature.id()}")
    print(f"Atributos: {feature.attributes()}")
    geom = feature.geometry()
    if geom.type() == QgsWkbTypes.PointGeometry:
        print(f"Punto: {geom.asPoint()}")

# Con filtro espacial
request = QgsFeatureRequest().setFilterRect(areaOfInterest)
for feature in layer.getFeatures(request):
    pass

# Con filtro de expresión
exp = QgsExpression('location_name ILIKE \'%Lake%\'')
request = QgsFeatureRequest(exp)
for feature in layer.getFeatures(request):
    pass

# Solo algunos campos (optimización)
request.setSubsetOfAttributes(['name', 'id'], layer.fields())
request.setFlags(QgsFeatureRequest.NoGeometry)  # Sin geometría
```

## 3. Plugin Structure

### 3.1 Archivos Requeridos

**Obligatorios:**

- `metadata.txt` - Información del plugin
- `__init__.py` - Punto de entrada con `classFactory()`
- `mainPlugin.py` - Código principal

**Opcionales:**

- `form.ui` - Diseño de GUI en Qt Designer
- `resources.qrc` - Recursos (iconos, etc.)
- `icon.png` - Icono del plugin
- `LICENSE` - Licencia (obligatorio si se publica)

### 3.2 metadata.txt

```ini
[general]
name=qAeroChart
qgisMinimumVersion=3.0
description=ICAO Aeronautical Chart Plugin
version=1.0
author=Tu Nombre
email=tu@email.com

about=Plugin para crear cartas aeronáuticas según estándares ICAO
    Incluye perfiles de aproximación, superficies, etc.

tracker=https://github.com/usuario/qAeroChart/issues
repository=https://github.com/usuario/qAeroChart
tags=aviation,aeronautical,ICAO,charts

homepage=https://github.com/usuario/qAeroChart
icon=icon.png
experimental=False
deprecated=False

category=Vector
```

### 3.3 **init**.py

```python
def classFactory(iface):
    from .qaerochart import QAeroChart
    return QAeroChart(iface)
```

### 3.4 Plugin Principal (qaerochart.py)

```python
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

class QAeroChart:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        # Crear acción
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.action = QAction(
            QIcon(icon_path),
            "qAeroChart",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)

        # Agregar a menú
        self.iface.addPluginToVectorMenu("&qAeroChart", self.action)
        # O toolbar
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&qAeroChart", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        # Código principal
        pass
```

### 3.5 DockWidget Pattern (como qOLS/TOFPA)

```python
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDockWidget

class QAeroChartDockWidget(QDockWidget):
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        super(QAeroChartDockWidget, self).__init__(parent)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

# En plugin principal
def initGui(self):
    self.dockwidget = QAeroChartDockWidget()
    self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
```

## 4. Layer Tree / TOC Management

### 4.1 Acceder al Layer Tree

```python
# Obtener root del proyecto
root = QgsProject.instance().layerTreeRoot()

# Listar todas las layers
for layer in QgsProject.instance().mapLayers().values():
    print(f"Layer: {layer.name()}")

# Buscar layer por nombre
country_layer = QgsProject.instance().mapLayersByName("countries")[0]

# Buscar por ID
layer = root.findLayer(layer_id)
```

### 4.2 Crear Grupos

```python
# Agregar grupo al root
node_group = root.addGroup('MAP 03 - Profile')

# Agregar sub-grupo
node_subgroup = node_group.addGroup('Sub Group')

# Agregar layer a grupo
node_group.addLayer(vlayer)

# O en posición específica
node_group.insertLayer(0, vlayer)

# Cambiar nombre
node_group.setName('New Name')

# Expandir/colapsar
node_group.setExpanded(True)

# Visibilidad
node_group.setItemVisibilityChecked(True)
```

### 4.3 Mover Layers en el TOC

```python
# Mover layer a otra posición
vl = QgsProject.instance().mapLayersByName("countries")[0]
myvl = root.findLayer(vl.id())
myvlclone = myvl.clone()
parent = myvl.parent()

# Mover al top del parent
parent.insertChildNode(0, myvlclone)
root.removeChildNode(myvl)

# O mover a otro grupo
group1 = root.addGroup("Group1")
group1.insertChildNode(0, myvlclone)
parent.removeChildNode(myvl)
```

### 4.4 Orden de Capas

```python
# Para organizar en orden específico dentro de un grupo
# Agregar layers en el orden deseado (de arriba a abajo):
group = root.addGroup('MAP 03 - Profile')
group.insertLayer(0, profile_MOCA_layer)      # Top
group.insertLayer(1, profile_dist_layer)
group.insertLayer(2, profile_line_layer)
group.insertLayer(3, profile_carto_label_layer)
group.insertLayer(4, profile_point_symbol_layer)  # Bottom
```

## 5. Geometry Handling

### 5.1 Crear Geometrías

```python
from qgis.core import QgsGeometry, QgsPoint, QgsPointXY

# Punto
point = QgsGeometry.fromPointXY(QgsPointXY(1, 1))
# O con Z
point = QgsGeometry.fromWkt("POINT(1 1 10)")

# Línea
points = [QgsPoint(0, 0), QgsPoint(1, 1), QgsPoint(2, 2)]
line = QgsGeometry.fromPolyline(points)

# Polígono (lista de anillos)
points = [[QgsPointXY(0, 0), QgsPointXY(1, 0), QgsPointXY(1, 1), QgsPointXY(0, 1)]]
polygon = QgsGeometry.fromPolygonXY(points)

# Desde WKT
geom = QgsGeometry.fromWkt("LINESTRING(0 0, 1 1, 2 2)")
```

### 5.2 Operaciones Geométricas

```python
# Buffer
buffered = geom.buffer(10, 5)  # distancia, segmentos

# Intersección
result = geom1.intersection(geom2)

# Unión
result = geom1.combine(geom2)

# Diferencia
result = geom1.difference(geom2)

# Distancia
dist = geom1.distance(geom2)

# Área / Longitud
area = geom.area()
length = geom.length()

# Centroide
centroid = geom.centroid()

# Bounding box
bbox = geom.boundingBox()
```

## 6. Coordinate Reference Systems

### 6.1 Obtener/Configurar CRS

```python
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform

# Crear CRS
crs = QgsCoordinateReferenceSystem("EPSG:4326")
crs_proj = QgsCoordinateReferenceSystem("EPSG:3857")

# CRS de un layer
layer_crs = layer.crs()

# CRS del proyecto
project_crs = QgsProject.instance().crs()

# Verificar validez
if crs.isValid():
    print(f"CRS válido: {crs.authid()}")
```

### 6.2 Transformación de Coordenadas

```python
# Crear transformación
transform = QgsCoordinateTransform(
    crs_source,
    crs_dest,
    QgsProject.instance()
)

# Transformar punto
point = QgsPointXY(lon, lat)
transformed_point = transform.transform(point)

# Transformar geometría
geom = QgsGeometry.fromPointXY(point)
geom.transform(transform)
```

## 7. Comunicación con el Usuario

### 7.1 Message Bar

```python
from qgis.core import Qgis

# Success
iface.messageBar().pushMessage(
    "Success",
    "Operation completed",
    level=Qgis.Success,
    duration=3
)

# Warning
iface.messageBar().pushMessage(
    "Warning",
    "Check your input",
    level=Qgis.Warning
)

# Error
iface.messageBar().pushMessage(
    "Error",
    "Operation failed",
    level=Qgis.Critical
)

# Info
iface.messageBar().pushMessage(
    "Info",
    "Processing...",
    level=Qgis.Info
)
```

### 7.2 Logging

```python
from qgis.core import QgsMessageLog, Qgis

QgsMessageLog.logMessage(
    "This is a message",
    "qAeroChart",
    level=Qgis.Info
)
```

## 8. Aplicación a qAeroChart

### 8.1 Profile Creation - Map Tool

```python
class ProfilePointTool(QgsMapToolEmitPoint):
    """Herramienta para seleccionar punto de referencia en el mapa"""

    pointSelected = pyqtSignal(QgsPointXY)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.marker = QgsVertexMarker(canvas)
        self.marker.setColor(QColor(255, 0, 0))
        self.marker.setIconSize(10)
        self.marker.setIconType(QgsVertexMarker.ICON_CROSS)
        self.marker.setPenWidth(2)

    def canvasPressEvent(self, e):
        # Obtener coordenadas del click
        point = self.toMapCoordinates(e.pos())

        # Mostrar marker
        self.marker.setCenter(point)
        self.marker.show()

        # Emitir señal
        self.pointSelected.emit(point)

    def deactivate(self):
        self.marker.hide()
        super().deactivate()
```

### 8.2 Memory Layers para Profile

```python
def create_profile_layers(self, group_name="MAP 03 - Profile"):
    """Crear las 5 memory layers del profile"""

    # Obtener CRS del proyecto
    project_crs = QgsProject.instance().crs()
    crs_str = project_crs.authid()

    # 1. Profile Point Symbol (puntos)
    profile_point = QgsVectorLayer(
        f"Point?crs={crs_str}&field=id:string&field=label:string&field=altitude:double&field=symbol_type:string",
        "profile_point_symbol",
        "memory"
    )

    # 2. Profile Carto Label (puntos para labels)
    profile_label = QgsVectorLayer(
        f"Point?crs={crs_str}&field=id:string&field=text:string&field=angle:double&field=size:double",
        "profile_carto_label",
        "memory"
    )

    # 3. Profile Line (líneas)
    profile_line = QgsVectorLayer(
        f"LineString?crs={crs_str}&field=id:string&field=type:string&field=style:string",
        "profile_line",
        "memory"
    )

    # 4. Profile Distance (anotaciones de distancia)
    profile_dist = QgsVectorLayer(
        f"Point?crs={crs_str}&field=id:string&field=distance:double&field=units:string",
        "profile_dist",
        "memory"
    )

    # 5. Profile MOCA (línea de MOCA)
    profile_moca = QgsVectorLayer(
        f"LineString?crs={crs_str}&field=id:string&field=moca_alt:double",
        "profile_MOCA",
        "memory"
    )

    # Agregar al proyecto con grupo
    root = QgsProject.instance().layerTreeRoot()

    # Crear grupo si no existe
    group = root.findGroup(group_name)
    if not group:
        group = root.addGroup(group_name)

    # Agregar layers en orden (de arriba a abajo en TOC)
    layers = [
        profile_moca,
        profile_dist,
        profile_line,
        profile_label,
        profile_point
    ]

    for layer in layers:
        QgsProject.instance().addMapLayer(layer, False)  # False = no agregar a root
        group.addLayer(layer)

    return {
        'point_symbol': profile_point,
        'carto_label': profile_label,
        'line': profile_line,
        'dist': profile_dist,
        'moca': profile_moca
    }
```

### 8.3 JSON Save/Load System

```python
import json

def save_profile_config(self, filepath, config_data):
    """Guardar configuración del profile a JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

    iface.messageBar().pushMessage(
        "Success",
        f"Profile saved to {filepath}",
        level=Qgis.Success
    )

def load_profile_config(self, filepath):
    """Cargar configuración del profile desde JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        iface.messageBar().pushMessage(
            "Success",
            f"Profile loaded from {filepath}",
            level=Qgis.Success
        )
        return config_data

    except Exception as e:
        iface.messageBar().pushMessage(
            "Error",
            f"Failed to load profile: {str(e)}",
            level=Qgis.Critical
        )
        return None
```

## 9. Patrones de qOLS/TOFPA a Seguir

### 9.1 Validación de Entrada Numérica

```python
# qOLS usa validadores personalizados en QLineEdit
# TOFPA usa QDoubleSpinBox directamente

# Opción 1: QDoubleSpinBox (más simple)
self.spinRunwayLength = QDoubleSpinBox()
self.spinRunwayLength.setRange(0.0, 10000.0)
self.spinRunwayLength.setDecimals(2)
self.spinRunwayLength.setSuffix(" m")

# Opción 2: QLineEdit con validador (más flexible)
from qgis.PyQt.QtGui import QDoubleValidator
validator = QDoubleValidator(0.0, 10000.0, 2)
validator.setNotation(QDoubleValidator.StandardNotation)
self.lineEditRunwayLength.setValidator(validator)
```

### 9.2 Status Indicators (como qOLS)

```python
# En .ui file, usar QLabel con colores para status
self.statusLabel = QLabel()
self.statusLabel.setStyleSheet("color: green;")
self.statusLabel.setText("✓ Ready")

# Actualizar status
def update_status(self, is_valid, message):
    if is_valid:
        self.statusLabel.setStyleSheet("color: green;")
        self.statusLabel.setText(f"✓ {message}")
    else:
        self.statusLabel.setStyleSheet("color: red;")
        self.statusLabel.setText(f"✗ {message}")
```

### 9.3 Signals Pattern

```python
# En DockWidget
class ProfileCreationDialog(QDialog):
    # Definir signals
    profileCreated = pyqtSignal(dict)  # dict con datos del profile
    cancelled = pyqtSignal()

    def accept(self):
        # Validar datos
        if self.validate_inputs():
            profile_data = self.gather_profile_data()
            self.profileCreated.emit(profile_data)
            super().accept()

    def reject(self):
        self.cancelled.emit()
        super().reject()

# En plugin principal
def show_profile_dialog(self):
    dialog = ProfileCreationDialog()
    dialog.profileCreated.connect(self.on_profile_created)
    dialog.cancelled.connect(self.on_profile_cancelled)
    dialog.exec_()
```

## 10. Referencias Útiles

### 10.1 Clases Principales

- **QgsVectorLayer** - Capa vectorial (archivo o memoria)
- **QgsFeature** - Feature individual
- **QgsGeometry** - Geometría
- **QgsField** - Definición de campo
- **QgsProject** - Proyecto actual
- **QgsMapCanvas** - Canvas del mapa
- **QgsMapTool** - Herramienta de mapa base
- **QgsRubberBand** - Feedback visual temporal
- **QgsLayerTreeGroup** - Grupo en TOC
- **QgisInterface** - Interfaz con QGIS (accesible como `iface`)

### 10.2 Módulos de Importación

```python
# Core
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsProject,
    QgsPointXY,
    QgsPoint,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsMessageLog,
    Qgis
)

# GUI
from qgis.gui import (
    QgsMapTool,
    QgsMapToolEmitPoint,
    QgsRubberBand,
    QgsVertexMarker,
    QgsMapCanvas
)

# PyQt5
from qgis.PyQt.QtCore import (
    Qt,
    QMetaType,
    pyqtSignal,
    QDateTime
)

from qgis.PyQt.QtWidgets import (
    QAction,
    QDialog,
    QDockWidget,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QTableWidget
)

from qgis.PyQt.QtGui import (
    QIcon,
    QColor
)
```

## 11. Debugging

### 11.1 Print Debugging (como qOLS/TOFPA)

```python
# Usar prefijo consistente para filtrar logs
print("PLUGIN qAeroChart: iniciando creación de profile")
print(f"PLUGIN qAeroChart: reference point = {point.x()}, {point.y()}")
```

### 11.2 QGIS Message Log

```python
QgsMessageLog.logMessage(
    "Detailed debug info here",
    "qAeroChart",
    level=Qgis.Info
)
```

### 11.3 Force Canvas Refresh

```python
# Si caching está habilitado
if iface.mapCanvas().isCachingEnabled():
    layer.triggerRepaint()
else:
    iface.mapCanvas().refresh()
```

## 12. Próximos Pasos

1. **Crear estructura base del plugin** - metadata.txt, **init**.py, qaerochart.py
2. **Diseñar profile_creation_dialog.ui** - Qt Designer con tabla dinámica
3. **Implementar ProfilePointTool** - QgsMapTool para selección de punto
4. **Crear memory layers** - Con esquema de campos apropiado
5. **Implementar tabla dinámica** - QTableWidget con add/remove rows
6. **Sistema JSON** - Save/load de configuraciones
7. **Generar geometrías** - Calcular posiciones basadas en runway/approach data

---

_Documento generado: 2025-01-21_  
_Basado en: QGIS 3.40 PyQGIS Developer Cookbook_
