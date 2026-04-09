"""
Create a horizontal scale bar (metres + feet) for aeronautical charts.

Defaults follow the standard aeronautical chart layout (Issue #69):
  - Metres: -400 (left) to +2500 (right), major every 500 m, minor every 100 m left
  - Feet  : -1000 (left) to +8000 (right), major every 1000 ft, minor every 100 ft left
  - Layer group: "Horizontal Scale" with two child layers:
      Lines : "Horizontal Scale - Lines"
      Labels: "Horizontal Scale - Labels"

Usage from QGIS Python console:
    from qAeroChart.scripts import Horizontal_Scale
    Horizontal_Scale.run_horizontal_scale(iface=iface)
"""

from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPoint,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
    QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
    QgsNullSymbolRenderer,
    QgsTextBufferSettings,
    Qgis,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont
from qgis.utils import iface

# Default parameters
METRE_RIGHT: int = 2500
METRE_LEFT: int = 400
METRE_RIGHT_STEP: int = 500
METRE_LEFT_STEP: int = 100
FT_RIGHT: int = 8000
FT_LEFT: int = 1000
FT_RIGHT_STEP: int = 1000
FT_LEFT_STEP: int = 100
TICK_LEN: float = 15.0
OFFSET: float = -50.0

_FT_TO_M: float = 0.3048


def _create_layer(name: str, geom: str, crs_authid: str, fields):
    layer = QgsVectorLayer(f"{geom}?crs={crs_authid}", name, "memory")
    layer.dataProvider().addAttributes(fields)
    layer.updateFields()
    return layer


def run_horizontal_scale(
    metre_right: int = METRE_RIGHT,
    metre_left: int = METRE_LEFT,
    metre_right_step: int = METRE_RIGHT_STEP,
    metre_left_step: int = METRE_LEFT_STEP,
    ft_right: int = FT_RIGHT,
    ft_left: int = FT_LEFT,
    ft_right_step: int = FT_RIGHT_STEP,
    ft_left_step: int = FT_LEFT_STEP,
    tick_len: float = TICK_LEN,
    offset: float = OFFSET,
    *,
    basepoint: QgsPoint = None,
    angle: float = None,
    name: str = "Horizontal Scale",
    **_,
):
    """Draw a double-sided horizontal scale bar on the current QGIS map.

    The bar is placed at *basepoint* along *angle*.  If neither is provided,
    the start of the currently selected guide line is used instead.

    Parameters
    ----------
    metre_right/metre_left:
        Map-unit extent (metres) on the positive/negative side.
    metre_right_step/metre_left_step:
        Major tick spacing on each side (metres).
    ft_right/ft_left:
        Extent on each side in feet.
    ft_right_step/ft_left_step:
        Major tick spacing on each side (feet).
    tick_len:
        Full tick height in map units (perpendicular to scale axis).
    offset:
        Perpendicular distance from the guide line / basepoint to the bar
        centreline (map units; negative = shift to the right-hand side).
    basepoint:
        Origin point (0-mark) of the scale on the map.
    angle:
        Azimuth (degrees) along which the scale extends.
    name:
        Layer group and base name for the created layers.
    """
    map_srid = iface.mapCanvas().mapSettings().destinationCrs().authid()

    if basepoint is None or angle is None:
        layer = iface.activeLayer()
        if not layer or not layer.selectedFeatureCount():
            iface.messageBar().pushMessage(
                "Horizontal Scale",
                "Select a guide line feature or set an origin/azimuth in the dock.",
                level=Qgis.Warning,
                duration=4,
            )
            return
        selection = list(layer.selectedFeatures())
        geom = selection[0].geometry().asPolyline()
        if not geom:
            iface.messageBar().pushMessage(
                "Horizontal Scale",
                "Selected feature is not a line.",
                level=Qgis.Critical,
                duration=4,
            )
            return
        start_point = QgsPoint(geom[0])
        end_point = QgsPoint(geom[-1])
        angle = start_point.azimuth(end_point)
        basepoint = start_point

    if not isinstance(basepoint, QgsPoint):
        basepoint = QgsPoint(basepoint)

    # Shift entire bar away from the guide line
    half_sp = tick_len * 0.5
    bar_centre = basepoint.project(abs(offset), angle + (90.0 if offset >= 0 else -90.0))
    base_m = bar_centre.project(half_sp, angle - 90.0)   # metres rail (above)
    base_f = bar_centre.project(half_sp, angle + 90.0)   # feet rail (below)

    line_fields = [
        QgsField("id", QVariant.String, len=255),
        QgsField("symbol", QVariant.String, len=25),
    ]
    label_fields = [
        QgsField("id", QVariant.String, len=255),
        QgsField("txt_label", QVariant.String, len=50),
    ]

    line_layer = _create_layer(f"{name} - Lines", "LineString", map_srid, line_fields)
    label_layer = _create_layer(f"{name} - Labels", "Point", map_srid, label_fields)

    _fid = [0]

    def add_line(pts, sym):
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPolyline(pts))
        f.setAttributes([str(_fid[0]), sym])
        _fid[0] += 1
        line_layer.dataProvider().addFeature(f)

    def add_label(pt, text):
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt)))
        f.setAttributes([str(_fid[0]), text])
        _fid[0] += 1
        label_layer.dataProvider().addFeature(f)

    def fwd(base, dist):
        return base.project(dist, angle)

    def bwd(base, dist):
        return base.project(dist, angle + 180.0)

    small_len = tick_len * 0.45
    lbl_off = tick_len * 1.3

    # ---- Metre rail ticks (upper rail, ticks go further up) ----
    m_pos_pts, m_neg_pts = [], []
    for v in range(0, metre_right + 1, metre_right_step):
        pt = fwd(base_m, float(v))
        add_line([pt, pt.project(tick_len, angle - 90.0)], "m_tick_pos")
        m_pos_pts.append(pt)
        add_label(pt.project(lbl_off, angle - 90.0), str(v))

    for v in range(metre_left_step, metre_left + 1, metre_left_step):
        pt = bwd(base_m, float(v))
        add_line([pt, pt.project(tick_len, angle - 90.0)], "m_tick_neg")
        m_neg_pts.append(pt)
        add_label(pt.project(lbl_off, angle - 90.0), str(v))

    # Minor ticks — positive side
    for v in range(metre_right_step // 2, metre_right, metre_right_step):
        pt = fwd(base_m, float(v))
        add_line([pt, pt.project(small_len, angle - 90.0)], "m_minor_pos")

    # Minor ticks — negative side
    for v in range(metre_left_step // 2, metre_left, metre_left_step):
        pt = bwd(base_m, float(v))
        add_line([pt, pt.project(small_len, angle - 90.0)], "m_minor_neg")

    # "METRES" header
    try:
        ctr = fwd(base_m, metre_right / 2.0)
        add_label(ctr.project(lbl_off * 1.8, angle - 90.0), "METRES")
    except Exception:
        pass

    # ---- Feet rail ticks (lower rail, ticks go down) ----
    ft_pos_pts, ft_neg_pts = [], []
    for v in range(0, ft_right + 1, ft_right_step):
        pt = fwd(base_f, v * _FT_TO_M)
        add_line([pt, pt.project(tick_len, angle + 90.0)], "ft_tick_pos")
        ft_pos_pts.append(pt)
        add_label(pt.project(lbl_off, angle + 90.0), str(v))

    for v in range(ft_left_step, ft_left + 1, ft_left_step):
        pt = bwd(base_f, v * _FT_TO_M)
        add_line([pt, pt.project(tick_len, angle + 90.0)], "ft_tick_neg")
        ft_neg_pts.append(pt)
        add_label(pt.project(lbl_off, angle + 90.0), str(v))

    # Minor ticks — positive side
    for v in range(ft_right_step // 2, ft_right, ft_right_step):
        pt = fwd(base_f, v * _FT_TO_M)
        add_line([pt, pt.project(small_len, angle + 90.0)], "ft_minor_pos")

    # Minor ticks — negative side
    for v in range(ft_left_step // 2, ft_left, ft_left_step):
        pt = bwd(base_f, v * _FT_TO_M)
        add_line([pt, pt.project(small_len, angle + 90.0)], "ft_minor_neg")

    # "FEET" footer
    try:
        ctr = fwd(base_f, (ft_right * _FT_TO_M) / 2.0)
        add_label(ctr.project(lbl_off * 1.8, angle + 90.0), "FEET")
    except Exception:
        pass

    # ---- Main spine lines ----
    if len(m_pos_pts) >= 2:
        add_line(m_pos_pts, "m_spine_pos")
    if m_neg_pts:
        add_line([m_pos_pts[0]] + m_neg_pts, "m_spine_neg")
    if len(ft_pos_pts) >= 2:
        add_line(ft_pos_pts, "ft_spine_pos")
    if ft_neg_pts:
        add_line([ft_pos_pts[0]] + ft_neg_pts, "ft_spine_neg")

    # Centre connector (joins the two rails at the origin)
    add_line([fwd(base_m, 0.0), fwd(base_f, 0.0)], "centre_connector")

    # ---- Styling ----
    try:
        sym = line_layer.renderer().symbol()
        sym.setColor(QColor("black"))
        sym.setWidth(0.25)
        line_layer.triggerRepaint()
    except Exception:
        pass

    try:
        label_layer.setRenderer(QgsNullSymbolRenderer())
    except Exception:
        try:
            pt_sym = QgsMarkerSymbol.createSimple({"color": "transparent", "size": "0"})
            label_layer.setRenderer(QgsSingleSymbolRenderer(pt_sym))
        except Exception:
            pass

    try:
        pal = QgsPalLayerSettings()
        pal.fieldName = "txt_label"
        pal.isExpression = False
        try:
            pal.placement = Qgis.LabelPlacement.OverPoint
        except Exception:
            pal.placement = QgsPalLayerSettings.OverPoint
        pal.enabled = True
        fmt = QgsTextFormat()
        fmt.setFont(QFont("Segoe UI", 8))
        fmt.setSize(8)
        fmt.setColor(QColor("black"))
        buf = QgsTextBufferSettings()
        buf.setEnabled(True)
        buf.setSize(0.6)
        buf.setColor(QColor("white"))
        fmt.setBuffer(buf)
        pal.setFormat(fmt)
        label_layer.setLabelsEnabled(True)
        label_layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
        label_layer.triggerRepaint()
    except Exception:
        pass

    # ---- Add to project ----
    root = QgsProject.instance().layerTreeRoot()
    group = root.findGroup(name)
    if group is None:
        root.insertGroup(0, name)  # insert at top (#88)
        group = root.findGroup(name)
    QgsProject.instance().addMapLayer(line_layer, False)
    QgsProject.instance().addMapLayer(label_layer, False)
    group.addLayer(line_layer)
    group.addLayer(label_layer)

    iface.messageBar().pushMessage(
        "Horizontal Scale",
        f"Created scale lines and labels for '{name}'.",
        level=Qgis.Success,
        duration=4,
    )


if __name__ == "__main__":
    run_horizontal_scale()
