"""OCA/H table builder — layout insertion script (Issue #74).

Usage inside QGIS Python console:
    from qAeroChart.scripts import table_oca_h
    table_oca_h.run(iface)
"""
from __future__ import annotations

try:
    from qgis.PyQt.QtGui import QColor, QFont
except ImportError:
    try:
        from PyQt6.QtGui import QColor, QFont  # type: ignore
    except ImportError:
        from PyQt5.QtGui import QColor, QFont  # type: ignore

from qgis.core import (
    QgsLayoutFrame,
    QgsLayoutItemManualTable,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPrintLayout,
    QgsProject,
    QgsTableCell,
    QgsTextFormat,
)
from qAeroChart.ui.oca_h_dialog import OcaHTableDialog
from qAeroChart.utils.qt_compat import Qt, QgsUnitTypes

TABLE_NAME = "oca_h_table"
TABLE_ID_PREFIX = "oca_table_"


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _next_table_id(layout, prefix: str) -> str:
    """Return the next sequential item ID for *prefix* in *layout*."""
    max_n = 0
    for item in layout.items():
        try:
            item_id = item.id()
            if item_id.startswith(prefix):
                n = int(item_id[len(prefix):])
                if n > max_n:
                    max_n = n
        except (AttributeError, ValueError):
            pass
    return f"{prefix}{max_n + 1:03d}"


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
    return [first_col_width] + [remaining / dynamic_cols] * dynamic_cols


def _classify_rows(table_rows: list[list[str]]) -> list[str]:
    """Classify each row as 'title', 'header', 'data', or 'footer'."""
    header_idx = None
    for i, row in enumerate(table_rows):
        if len(row) > 1 and any(row[j] for j in range(1, len(row))):
            header_idx = i
            break
    types: list[str] = []
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
    row_types = _classify_rows(table_rows)
    styled: list[list[QgsTableCell]] = []
    for r, row in enumerate(table_rows):
        rtype = row_types[r]
        styled_row: list[QgsTableCell] = []
        for c, val in enumerate(row):
            cell = QgsTableCell(val)
            fmt = QgsTextFormat()
            font = QFont(font_family)
            if rtype in ("title", "footer", "header"):
                font.setBold(True)
            fmt.setFont(font)
            fmt.setSize(font_size)
            cell.setTextFormat(fmt)
            if rtype in ("title", "footer", "header") or c >= 1:
                cell.setHorizontalAlignment(Qt.AlignHCenter)
            styled_row.append(cell)
        styled.append(styled_row)
    return styled


def _get_or_create_layout(name: str, project) -> QgsPrintLayout:
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
    for mf in list(layout.multiFrames()):
        if hasattr(mf, "customProperty") and mf.customProperty("name") == TABLE_NAME:
            layout.removeMultiFrame(mf)


def _build_table(table_rows: list[list[str]], cfg: dict, layout) -> None:
    t = QgsLayoutItemManualTable.create(layout)
    t.setTableContents(_build_styled_cells(table_rows, cfg["font_family"], cfg["font_size"]))
    t.setGridStrokeWidth(cfg["stroke"])
    try:
        t.setCellMargin(cfg["cell_margin"])
    except Exception:
        pass
    t.setGridColor(QColor(0, 0, 0, 255))
    t.setCustomProperty("name", TABLE_NAME)

    text_format = QgsTextFormat()
    text_format.setFont(QFont(cfg["font_family"]))
    text_format.setSize(cfg["font_size"])
    t.setContentTextFormat(text_format)

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
            computed_height = max(
                cfg["height"],
                rows * per_row + 2 * cfg["cell_margin"] + cfg["stroke"],
            )
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
    frame.attemptMove(
        QgsLayoutPoint(x_pos, y_pos, QgsUnitTypes.LayoutMillimeters)
    )

    item_id = _next_table_id(layout, TABLE_ID_PREFIX)
    frame.setId(item_id)
    try:
        frame.setDisplayName(item_id)
    except Exception:
        pass

    t.addFrame(frame)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def build_dialog(
    iface=None, parent=None, default_layout_name: str | None = None
) -> OcaHTableDialog:
    dlg = OcaHTableDialog(iface=iface, parent=parent)
    if default_layout_name:
        dlg.select_layout(default_layout_name)
    return dlg


def insert_from_dialog(dlg: OcaHTableDialog, iface=None) -> None:
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
    layout.refresh()
    n_data = len(table_rows)
    if iface:
        iface.messageBar().pushInfo(
            "OCA/H Table",
            f"Table added to layout '{layout.name()}' with {n_data} rows.",
        )
    else:
        print(f"Table added to layout '{layout.name()}' with {n_data} rows.")


def run(iface=None, default_layout_name: str | None = None, parent_window=None, **_) -> None:
    dlg = build_dialog(iface=iface, parent=parent_window, default_layout_name=default_layout_name)
    result = (dlg.exec_ if hasattr(dlg, "exec_") else dlg.exec)()
    if not result:
        return
    insert_from_dialog(dlg, iface)
