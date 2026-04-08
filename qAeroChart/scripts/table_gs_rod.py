"""GS / Rate-of-Descent table builder — layout insertion script (Issue #73).

Usage inside QGIS Python console:
    from qAeroChart.scripts import table_gs_rod
    table_gs_rod.run(iface)
"""
from __future__ import annotations

try:
    from qgis.PyQt import QtWidgets
    from qgis.PyQt.QtGui import QColor, QFont
except ImportError:
    try:
        from PyQt6 import QtWidgets  # type: ignore
        from PyQt6.QtGui import QColor, QFont  # type: ignore
    except ImportError:
        from PyQt5 import QtWidgets  # type: ignore
        from PyQt5.QtGui import QColor, QFont  # type: ignore

from qgis.core import (
    QgsProject,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLayoutItemManualTable,
    QgsTableCell,
    QgsTextFormat,
    QgsLayoutFrame,
    QgsPrintLayout,
)
from qAeroChart.utils.qt_compat import QgsUnitTypes, Qt
from qAeroChart.ui.gs_rod_dialog import GsRodTableDialog

TABLE_NAME = "gs_rod_table"


# ------------------------------------------------------------------
# Internal helpers (mirror table_distance_altitude.py)
# ------------------------------------------------------------------

def _calc_column_widths(
    total_width: float,
    first_col_width: float,
    num_columns: int,
    stroke_width: float,
    cell_margin: float,
) -> list[float]:
    if num_columns < 1:
        return []
    if num_columns == 1:
        return [total_width]
    dynamic_cols = num_columns - 1
    extra_width = (num_columns - 1) * stroke_width + 2 * cell_margin * num_columns
    remaining = total_width - first_col_width - extra_width
    if remaining <= 0:
        return [total_width / num_columns] * num_columns
    dynamic_col_width = remaining / dynamic_cols
    return [first_col_width] + [dynamic_col_width] * dynamic_cols


def _classify_rows(table_rows: list[list[str]]) -> list[str]:
    """Classify each row as 'title', 'header', 'data', or 'footer'."""
    header_idx = None
    for i, row in enumerate(table_rows):
        if len(row) > 2 and any(row[j] for j in range(2, len(row))):
            header_idx = i
            break
    types = []
    for i, row in enumerate(table_rows):
        is_span = len(row) > 1 and all(c == "" for c in row[1:])
        if is_span:
            types.append("footer" if header_idx is not None and i > header_idx else "title")
        elif i == header_idx:
            types.append("header")
        else:
            types.append("data")
    return types


def _build_styled_cells(
    table_rows: list[list[str]], font_family: str, font_size: float
) -> list[list[QgsTableCell]]:
    """Return a grid of QgsTableCell with bold and alignment applied."""
    row_types = _classify_rows(table_rows)
    styled = []
    for r, row in enumerate(table_rows):
        rtype = row_types[r]
        styled_row = []
        for c, val in enumerate(row):
            cell = QgsTableCell(val)
            fmt = QgsTextFormat()
            font = QFont(font_family)
            if rtype == "title" or (rtype == "header" and c >= 2):
                font.setBold(True)
            fmt.setFont(font)
            fmt.setSize(font_size)
            cell.setTextFormat(fmt)
            if rtype == "title" or c >= 1:
                cell.setHorizontalAlignment(Qt.AlignHCenter)
            styled_row.append(cell)
        styled.append(styled_row)
    return styled


def _get_or_create_layout(name: str, project):
    manager = project.layoutManager()
    for lyt in manager.layouts():
        if lyt.name() == name:
            return lyt
    lyt = QgsPrintLayout(project)
    lyt.initializeDefaults()
    lyt.setName(name or "AutoLayout")
    manager.addLayout(lyt)
    return lyt


def _remove_existing_table(layout) -> None:
    for item in layout.items():
        if hasattr(item, "customProperty") and item.customProperty("name") == TABLE_NAME:
            layout.removeLayoutItem(item)
            break


def _build_table(table_rows: list[list[str]], cfg: dict, layout) -> None:
    t = QgsLayoutItemManualTable.create(layout)
    t.setTableContents(_build_styled_cells(table_rows, cfg["font_family"], cfg["font_size"]))
    t.setGridStrokeWidth(cfg["stroke"])
    try:
        t.setCellMargin(cfg["cell_margin"])
    except Exception:
        pass
    t.setCustomProperty("name", TABLE_NAME)

    text_format = QgsTextFormat()
    text_format.setFont(QFont(cfg["font_family"]))
    text_format.setSize(cfg["font_size"])
    t.setContentTextFormat(text_format)
    t.setGridColor(QColor(0, 0, 0, 255))

    layout.addMultiFrame(t)

    col_widths = _calc_column_widths(
        cfg["total_width"],
        cfg["first_col_width"],
        len(table_rows[0]) if table_rows else 0,
        cfg["stroke"],
        cfg["cell_margin"],
    )
    if col_widths:
        t.setColumnWidths(col_widths)

    computed_height = cfg["height"]
    try:
        rows = len(table_rows)
        if rows > 0:
            per_row = max(cfg.get("font_size", 8.0) * 2.2, 8.0)
            computed_height = max(cfg["height"], rows * per_row + 2 * cfg["cell_margin"] + cfg["stroke"])
    except Exception:
        pass

    x_pos = cfg["x"]
    y_pos = cfg["y"]
    try:
        pages = layout.pageCollection().pages()
        if pages:
            page_size = pages[0].pageSize()
            if cfg["x"] is None or cfg["x"] <= 0:
                x_pos = (page_size.width() - cfg["total_width"]) / 2.0
            if cfg["y"] is None or cfg["y"] <= 0 or cfg["y"] >= page_size.height() * 0.6:
                y_pos = (page_size.height() - computed_height) / 2.0
    except Exception:
        pass

    frame = QgsLayoutFrame(layout, t)
    frame.attemptResize(
        QgsLayoutSize(cfg["total_width"], computed_height, QgsUnitTypes.LayoutMillimeters)
    )
    frame.attemptMove(QgsLayoutPoint(x_pos, y_pos, QgsUnitTypes.LayoutMillimeters))
    t.addFrame(frame)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def build_dialog(iface=None, parent=None, default_layout_name: str | None = None) -> GsRodTableDialog:
    """Create and configure the dialog without showing it (non-blocking flow)."""
    dlg = GsRodTableDialog(iface=iface, parent=parent)
    if default_layout_name:
        dlg.select_layout(default_layout_name)
    return dlg


def insert_from_dialog(dlg: GsRodTableDialog, iface=None) -> None:
    """Read data from an accepted dialog and insert the table into the chosen layout."""
    table_rows = dlg.table_data()
    cfg = dlg.config()
    layout_name = cfg["layout_name"]
    if not layout_name or layout_name.startswith("("):
        layout_name = "AutoLayout"
        cfg = {**cfg, "layout_name": layout_name}
    project = QgsProject.instance()
    layout = _get_or_create_layout(layout_name, project)
    _remove_existing_table(layout)
    _build_table(table_rows, cfg, layout)
    n_cols = len(table_rows[0]) - 2 if table_rows else 0  # subtract label + unit cols
    if iface:
        iface.messageBar().pushInfo(
            "GS/ROD Table",
            f"Table added to layout '{layout.name()}' with {n_cols} GS columns.",
        )
    else:
        print(f"Table added to layout '{layout.name()}' with {n_cols} GS columns.")


def run(iface=None, default_layout_name: str | None = None, parent_window=None, **_) -> None:
    """Open the dialog, then add the table to the chosen layout.

    Blocking version kept for backward-compat (e.g. Python console usage).
    """
    dlg = build_dialog(iface=iface, parent=parent_window, default_layout_name=default_layout_name)
    result = (dlg.exec_ if hasattr(dlg, "exec_") else dlg.exec)()
    if not result:
        return
    insert_from_dialog(dlg, iface)
