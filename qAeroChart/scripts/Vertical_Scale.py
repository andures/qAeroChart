"""
Create a vertical scale (lines + labels) for Type A charts.

Defaults follow the provided spec:
- Vertical scale: 1:10 000 (configurable)
- Meters: 0..100 every 25 m on the right
- Feet: 0..300 every 50 ft on the left
- Layer group: "Vertical Scale" with two child layers:
  - Lines: "Vertical Scale"
  - Labels: "carto-vertical-scale-label"

Usage: select a guide line (baseline) to orient the scale, then run this script.
"""

from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPoint,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
    Qgis,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

# Editable parameters
SCALE_DENOMINATOR = 10000  # default vertical scale 1:10 000
OFFSET = -50.0             # shift from the selected guide line (map units)
TICK_LEN = 15.0            # tick length (map units)
M_MAX = 100                # meters max
M_STEP = 25                # meters step
FT_MAX = 300               # feet max
FT_STEP = 50               # feet step


def _scale_factor(denominator: float) -> float:
    """Convert real meters to map units based on vertical scale denominator.

    For a denominator of 10 000, 100 m → 100 * (10 000 / 1000) = 1000 map units.
    """
    try:
        return float(denominator) / 1000.0
    except Exception:
        return 10.0


def _create_layer(name: str, geom: str, crs_authid: str, fields):
    layer = QgsVectorLayer(f"{geom}?crs={crs_authid}", name, "memory")
    layer.dataProvider().addAttributes(fields)
    layer.updateFields()
    return layer


def run_vertical_scale(
    scale_denominator: float = SCALE_DENOMINATOR,
    offset: float = OFFSET,
    tick_len: float = TICK_LEN,
    m_max: int = M_MAX,
    m_step: int = M_STEP,
    ft_max: int = FT_MAX,
    ft_step: int = FT_STEP,
):
    map_srid = iface.mapCanvas().mapSettings().destinationCrs().authid()

    # Require a selected line to orient the scale
    layer = iface.activeLayer()
    if not layer or not layer.selectedFeatureCount():
        iface.messageBar().pushMessage(
            "Vertical Scale",
            "Select a guide line feature before running the script.",
            level=Qgis.Warning,
            duration=4,
        )
        return
    selection = layer.selectedFeatures()
    geom = selection[0].geometry().asPolyline()
    if not geom:
        iface.messageBar().pushMessage(
            "Vertical Scale",
            "Selected feature is not a line.",
            level=Qgis.Critical,
            duration=4,
        )
        return

    start_point = QgsPoint(geom[0])
    end_point = QgsPoint(geom[-1])
    angle = start_point.azimuth(end_point)

    factor = _scale_factor(scale_denominator)
    basepoint = start_point.project(offset, angle - 90)

    # Prepare layers
    line_fields = [QgsField('id', QVariant.String, len=255), QgsField('symbol', QVariant.String, len=25)]
    label_fields = [QgsField('id', QVariant.String, len=255), QgsField('txt_label', QVariant.String, len=50)]

    line_layer = _create_layer("Vertical Scale", "Linestring", map_srid, line_fields)
    label_layer = _create_layer("carto-vertical-scale-label", "Point", map_srid, label_fields)

    def add_line(points, symbol_val):
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPolyline(points))
        f.setAttributes([symbol_val, symbol_val])
        line_layer.dataProvider().addFeature(f)

    def add_label(point, text, label_id):
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
        f.setAttributes([label_id, text])
        label_layer.dataProvider().addFeature(f)

    # Meter side (right)
    meter_ticks = []
    for val_m in range(0, m_max + 1, m_step):
        dist = val_m * factor
        p0 = basepoint.project(dist, angle)
        p1 = p0.project(tick_len, angle + 90)
        meter_ticks.append(p0)
        add_line([p0, p1], "m_tick")
        # label slightly beyond tick
        p_label = p1.project(tick_len * 0.6, angle + 90)
        add_label(p_label, str(val_m), f"m_{val_m}")

    # Feet side (left)
    feet_ticks = []
    for val_ft in range(0, ft_max + 1, ft_step):
        meters = val_ft * 0.3048
        dist = meters * factor
        p0 = basepoint.project(dist, angle)
        p1 = p0.project(tick_len, angle - 90)
        feet_ticks.append(p0)
        add_line([p0, p1], "ft_tick")
        p_label = p1.project(tick_len * 0.6, angle - 90)
        add_label(p_label, str(val_ft), f"ft_{val_ft}")

    # Main line (use meter side extent)
    if meter_ticks:
        add_line(meter_ticks, "scale_line")

    # Top connector between sides
    if meter_ticks and feet_ticks:
        add_line([meter_ticks[-1], feet_ticks[-1]], "top_connect")

    # Add static labels: units and title/scale at bottom
    try:
        # Meters header near top right
        top_m = meter_ticks[-1].project(tick_len * 1.2, angle + 90)
        add_label(top_m, "METERS", "lbl_meters")
        # Feet header near top left
        top_ft = feet_ticks[-1].project(tick_len * 1.2, angle - 90)
        add_label(top_ft, "FEET", "lbl_feet")
        # Bottom title
        bottom = basepoint.project(-tick_len * 2.5, angle)
        add_label(bottom, "VERTICAL", "lbl_vertical")
        add_label(bottom.project(tick_len * 1.5, angle), "SCALE", "lbl_scale")
        add_label(bottom.project(tick_len * 3.0, angle), f"1:{int(scale_denominator):,}".replace(',', ' '), "lbl_ratio")
    except Exception:
        pass

    # Basic styling: black thin lines
    try:
        line_renderer = line_layer.renderer()
        sym = line_renderer.symbol()
        sym.setColor(QColor("black"))
        sym.setWidth(0.25)
        line_layer.triggerRepaint()
    except Exception:
        pass

    # Add to project under a group
    root = QgsProject.instance().layerTreeRoot()
    group = root.findGroup("Vertical Scale") or root.addGroup("Vertical Scale")
    QgsProject.instance().addMapLayer(line_layer, False)
    QgsProject.instance().addMapLayer(label_layer, False)
    group.addLayer(line_layer)
    group.addLayer(label_layer)

    iface.messageBar().pushMessage(
        "Vertical Scale",
        "Created scale lines and labels (meters/feet).",
        level=Qgis.Success,
        duration=4,
    )


if __name__ == "__main__":
    run_vertical_scale()