# -*- coding: utf-8 -*-
"""
VerticalScaleDockWidget — standalone QDockWidget for creating and managing
vertical scale bars on the QGIS map canvas.

Architecture
------------
- Two-page QStackedWidget: menu page (list of saved scales) and form page
  (new/edit inputs).
- All persistence goes through VerticalScaleController; this widget never
  touches VerticalScaleManager directly.
- All drawing goes through VerticalScaleController.run_scale().
- Origin point is captured via ProfilePointTool (map canvas tool).

PyQt compatibility
------------------
All Qt imports use ``qgis.PyQt.*`` which is available in every QGIS version.
"""
from __future__ import annotations

from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QLabel,
    QMessageBox,
    QShortcut,
    QInputDialog,
    QMenu,
    QAction,
)
from qgis.PyQt.QtGui import QKeySequence
from qgis.core import QgsPointXY

from .core.vertical_scale_controller import VerticalScaleController
from .utils.logger import log

# Page indices in the QStackedWidget
_PAGE_MENU = 0
_PAGE_FORM = 1


class VerticalScaleDockWidget(QDockWidget):
    """Standalone dock widget for vertical scale management."""

    # Shared QSS constants — single source of truth, mirrors the .ui file
    # so both docks are visually identical.
    _BTN_H = 35          # standard button height (px)
    _BTN_H_FORM = 32     # form-action button height (px)

    _QSS_BTN_GREEN = (
        "background-color: #4CAF50; color: white; font-weight: bold;"
    )
    _QSS_BTN_RED = "background-color: #f44336; color: white;"
    _QSS_BTN_BLUE = "background-color: #1976D2; color: white;"
    _QSS_LIST = (
        "QListWidget::item { padding: 8px; border-bottom: 1px solid #e0e0e0; }"
        "QListWidget::item:selected { background-color: #e3f2fd; color: black; }"
        "QListWidget::item:hover { background-color: #f5f5f5; }"
    )

    closing = pyqtSignal()

    def __init__(
        self,
        controller: VerticalScaleController,
        iface: object | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Vertical Scale", parent)
        self._controller = controller
        self._iface = iface
        self._origin: QgsPointXY | None = None
        self._point_tool = None
        self._previous_tool = None

        self._build_ui()
        self._connect_signals()
        self._refresh_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_menu_page())   # index 0
        self._stack.addWidget(self._build_form_page())   # index 1

        self.setWidget(container)
        self.setMinimumWidth(280)

    def _build_menu_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)

        # ---- Group box header — same style as "📂 Profile Charts" in .ui ----
        grp = QGroupBox("📐 Vertical Scales")
        grp_layout = QVBoxLayout(grp)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SingleSelection)
        self._list.setMinimumHeight(200)
        self._list.setStyleSheet(self._QSS_LIST)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemDoubleClicked.connect(self._on_run_selected)
        grp_layout.addWidget(self._list)

        # ---- Action buttons (height 35 + emoji — mirrors profile dock) ----
        btn_row = QHBoxLayout()

        self._btn_new = QPushButton("➕ New…")
        self._btn_new.setMinimumHeight(self._BTN_H)
        self._btn_new.setStyleSheet(self._QSS_BTN_GREEN)

        self._btn_run = QPushButton("📍 Run")
        self._btn_run.setMinimumHeight(self._BTN_H)
        self._btn_run.setEnabled(False)

        self._btn_edit = QPushButton("✏️ Edit…")
        self._btn_edit.setMinimumHeight(self._BTN_H)
        self._btn_edit.setEnabled(False)

        self._btn_delete = QPushButton("🗑️ Delete")
        self._btn_delete.setMinimumHeight(self._BTN_H)
        self._btn_delete.setStyleSheet(self._QSS_BTN_RED)
        self._btn_delete.setEnabled(False)

        for btn in (self._btn_new, self._btn_run, self._btn_edit, self._btn_delete):
            btn_row.addWidget(btn)
        grp_layout.addLayout(btn_row)

        layout.addWidget(grp)
        layout.addStretch()

        # F2 → rename inline (same as profile dock)
        self._rename_shortcut = QShortcut(QKeySequence(Qt.Key_F2), self._list)
        self._rename_shortcut.activated.connect(self._rename_selected)

        return page

    def _build_form_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # ---- Back button — same "← Back to Menu" pattern as profile dock ----
        self._btn_back = QPushButton("← Back to Menu")
        layout.addWidget(self._btn_back)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(6)

        # ---- Origin ----
        grp_origin = QGroupBox("📍 Origin")
        origin_form = QFormLayout(grp_origin)
        origin_row = QHBoxLayout()
        self._line_origin = QLineEdit()
        self._line_origin.setReadOnly(True)
        self._line_origin.setPlaceholderText("Click 'Pick' to select on map…")
        self._btn_pick = QPushButton("📍 Pick…")
        self._btn_pick.setFixedWidth(70)
        origin_row.addWidget(self._line_origin)
        origin_row.addWidget(self._btn_pick)
        origin_form.addRow("Origin:", origin_row)
        inner_layout.addWidget(grp_origin)

        # ---- Parameters ----
        grp_basic = QGroupBox("⚙️ Parameters")
        basic_form = QFormLayout(grp_basic)

        self._line_name = QLineEdit("Vertical Scale")
        basic_form.addRow("Name:", self._line_name)

        self._spin_azimuth = QSpinBox()
        self._spin_azimuth.setRange(0, 359)
        self._spin_azimuth.setValue(90)
        self._spin_azimuth.setSuffix(" °")
        basic_form.addRow("Azimuth:", self._spin_azimuth)

        self._spin_scale = QSpinBox()
        self._spin_scale.setRange(1000, 100000)
        self._spin_scale.setSingleStep(1000)
        self._spin_scale.setValue(10000)
        self._spin_scale.setPrefix("1:")
        basic_form.addRow("Scale:", self._spin_scale)

        self._dspin_offset = QDoubleSpinBox()
        self._dspin_offset.setRange(-5000.0, 5000.0)
        self._dspin_offset.setSingleStep(10.0)
        self._dspin_offset.setValue(-50.0)
        self._dspin_offset.setSuffix(" m")
        basic_form.addRow("Offset:", self._dspin_offset)

        self._dspin_tick = QDoubleSpinBox()
        self._dspin_tick.setRange(1.0, 200.0)
        self._dspin_tick.setSingleStep(1.0)
        self._dspin_tick.setValue(15.0)
        self._dspin_tick.setSuffix(" m")
        basic_form.addRow("Tick length:", self._dspin_tick)

        inner_layout.addWidget(grp_basic)

        # ---- Metres ----
        grp_m = QGroupBox("📏 Metres")
        m_form = QFormLayout(grp_m)
        self._spin_m_max = QSpinBox()
        self._spin_m_max.setRange(10, 10000)
        self._spin_m_max.setValue(100)
        m_form.addRow("Max (m):", self._spin_m_max)

        self._spin_m_step = QSpinBox()
        self._spin_m_step.setRange(1, 1000)
        self._spin_m_step.setValue(25)
        m_form.addRow("Step (m):", self._spin_m_step)
        inner_layout.addWidget(grp_m)

        # ---- Feet ----
        grp_ft = QGroupBox("📏 Feet")
        ft_form = QFormLayout(grp_ft)
        self._spin_ft_max = QSpinBox()
        self._spin_ft_max.setRange(10, 50000)
        self._spin_ft_max.setValue(300)
        ft_form.addRow("Max (ft):", self._spin_ft_max)

        self._spin_ft_step = QSpinBox()
        self._spin_ft_step.setRange(1, 5000)
        self._spin_ft_step.setValue(50)
        ft_form.addRow("Step (ft):", self._spin_ft_step)
        inner_layout.addWidget(grp_ft)
        inner_layout.addStretch()

        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        # ---- Separator ----
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep)

        # ---- Form action buttons — same heights/styles as profile form ----
        btn_row = QHBoxLayout()

        self._btn_run_form = QPushButton("📐 Generate Scale")
        self._btn_run_form.setMinimumHeight(self._BTN_H_FORM)
        self._btn_run_form.setStyleSheet(
            self._QSS_BTN_GREEN + f" min-height: {self._BTN_H_FORM}px;"
        )

        self._btn_cancel = QPushButton("✖ Cancel")
        self._btn_cancel.setMinimumHeight(self._BTN_H_FORM)
        self._btn_cancel.setStyleSheet(f"min-height: {self._BTN_H_FORM}px;")

        btn_row.addWidget(self._btn_run_form)
        btn_row.addWidget(self._btn_cancel)
        layout.addLayout(btn_row)

        return page

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._btn_new.clicked.connect(self._on_new)
        self._btn_run.clicked.connect(self._on_run_selected)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_back.clicked.connect(self.show_menu)
        self._btn_pick.clicked.connect(self._on_pick_origin)
        self._btn_run_form.clicked.connect(self._on_run_form)
        self._btn_cancel.clicked.connect(self.show_menu)

        self._list.itemSelectionChanged.connect(self._on_scale_selection_changed)

        self._controller.scales_changed.connect(self._refresh_list)
        self._controller.message.connect(self._show_message)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def show_menu(self) -> None:
        """Switch back to the menu page."""
        self._cancel_pick()
        self._stack.setCurrentIndex(_PAGE_MENU)

    def showEvent(self, event) -> None:  # noqa: N802
        """Always return to menu page when the dock is shown."""
        super().showEvent(event)
        self._stack.setCurrentIndex(_PAGE_MENU)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._cancel_pick()
        self.closing.emit()
        super().closeEvent(event)

    def _on_scale_selection_changed(self) -> None:
        has_sel = bool(self._list.selectedItems())
        self._btn_run.setEnabled(has_sel)
        self._btn_edit.setEnabled(has_sel)
        self._btn_delete.setEnabled(has_sel)

    # ------------------------------------------------------------------
    # Menu page slots
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        self._list.clear()
        for meta in self._controller.get_all_scales():
            text = f"{meta.get('name', '?')}  (az {meta.get('angle', '?')}°)" \
                if 'angle' in meta else meta.get('name', '?')
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, meta.get("id"))
            self._list.addItem(item)

    def _selected_id(self) -> str | None:
        items = self._list.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def _on_new(self) -> None:
        self._reset_form()
        self._stack.setCurrentIndex(_PAGE_FORM)

    def _on_run_selected(self) -> None:
        sid = self._selected_id()
        if not sid:
            QMessageBox.information(self, "Vertical Scale", "Please select a scale first.")
            return
        configs = {
            c.get("id", c.get("name")): c
            for c in self._controller._scale_manager.load_all_configs()
        }
        cfg = configs.get(sid)
        if cfg is None:
            QMessageBox.warning(self, "Vertical Scale", "Could not load scale configuration.")
            return
        self._controller.run_scale(cfg)

    def _on_edit(self) -> None:
        sid = self._selected_id()
        if not sid:
            QMessageBox.information(self, "Vertical Scale", "Please select a scale first.")
            return
        cfg = self._controller._scale_manager.get_config(sid)
        if cfg is None:
            return
        self._populate_form(cfg)
        self._stack.setCurrentIndex(_PAGE_FORM)

    def _on_delete(self) -> None:
        sid = self._selected_id()
        if not sid:
            return
        if QMessageBox.question(
            self, "Delete Scale",
            "Delete this vertical scale permanently?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            self._controller.delete_scale(sid)

    def _rename_selected(self) -> None:
        sid = self._selected_id()
        if not sid:
            return
        current_items = self._list.selectedItems()
        current_name = current_items[0].text().split("  (az")[0] if current_items else ""
        new_name, ok = QInputDialog.getText(
            self, "Rename Scale", "New name:", text=current_name
        )
        if ok and new_name.strip():
            self._controller.rename_scale(sid, new_name.strip())

    def _on_context_menu(self, pos) -> None:
        sid = self._selected_id()
        if not sid:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Rename… (F2)")
        delete_action = menu.addAction("Delete")
        action = menu.exec_(self._list.viewport().mapToGlobal(pos))
        if action == rename_action:
            self._rename_selected()
        elif action == delete_action:
            self._on_delete()

    # ------------------------------------------------------------------
    # Form page slots
    # ------------------------------------------------------------------

    def _on_pick_origin(self) -> None:
        """Activate the map tool to select an origin point."""
        if self._iface is None:
            QMessageBox.warning(self, "Vertical Scale", "Map canvas not available.")
            return
        try:
            canvas = self._iface.mapCanvas()
            from .tools.profile_point_tool import ProfilePointTool
            self._previous_tool = canvas.mapTool()
            self._point_tool = ProfilePointTool(canvas)
            self._point_tool.originSelected.connect(self._on_origin_selected)
            canvas.setMapTool(self._point_tool)
            self._line_origin.setPlaceholderText("Click on map to pick origin…")
        except Exception as e:
            log(f"Could not activate origin picker: {e}", "ERROR")
            QMessageBox.warning(self, "Vertical Scale", f"Could not activate map tool: {e}")

    def _on_origin_selected(self, point: QgsPointXY) -> None:
        """Called when user clicks on the map."""
        self._origin = point
        self._line_origin.setText(f"{point.x():.4f}, {point.y():.4f}")
        self._cancel_pick()

    def _cancel_pick(self) -> None:
        """Deactivate the map tool and restore the previous one."""
        if self._point_tool is None:
            return
        try:
            canvas = self._iface.mapCanvas()
            if self._previous_tool:
                canvas.setMapTool(self._previous_tool)
            else:
                canvas.unsetMapTool(self._point_tool)
        except Exception:
            pass
        finally:
            self._point_tool = None
            self._previous_tool = None

    def _on_run_form(self) -> None:
        if self._origin is None:
            QMessageBox.warning(self, "Vertical Scale", "Please pick an origin point on the map.")
            return
        name = self._line_name.text().strip() or "Vertical Scale"
        params = {
            "name": name,
            "angle": float(self._spin_azimuth.value()),
            "basepoint": {"x": self._origin.x(), "y": self._origin.y()},
            "scale_denominator": float(self._spin_scale.value()),
            "offset": self._dspin_offset.value(),
            "tick_len": self._dspin_tick.value(),
            "m_max": self._spin_m_max.value(),
            "m_step": self._spin_m_step.value(),
            "ft_max": self._spin_ft_max.value(),
            "ft_step": self._spin_ft_step.value(),
        }
        self._controller.run_scale(params)
        self.show_menu()

    # ------------------------------------------------------------------
    # Form helpers
    # ------------------------------------------------------------------

    def _reset_form(self) -> None:
        self._origin = None
        self._line_origin.clear()
        self._line_name.setText("Vertical Scale")
        self._spin_azimuth.setValue(90)
        self._spin_scale.setValue(10000)
        self._dspin_offset.setValue(-50.0)
        self._dspin_tick.setValue(15.0)
        self._spin_m_max.setValue(100)
        self._spin_m_step.setValue(25)
        self._spin_ft_max.setValue(300)
        self._spin_ft_step.setValue(50)

    def _populate_form(self, cfg: dict) -> None:
        self._origin = None
        bp = cfg.get("basepoint", {})
        if bp:
            try:
                self._origin = QgsPointXY(float(bp["x"]), float(bp["y"]))
                self._line_origin.setText(f"{self._origin.x():.4f}, {self._origin.y():.4f}")
            except (KeyError, TypeError, ValueError):
                self._line_origin.clear()
        self._line_name.setText(cfg.get("name", "Vertical Scale"))
        self._spin_azimuth.setValue(int(cfg.get("angle", 90)))
        self._spin_scale.setValue(int(cfg.get("scale_denominator", 10000)))
        self._dspin_offset.setValue(float(cfg.get("offset", -50.0)))
        self._dspin_tick.setValue(float(cfg.get("tick_len", 15.0)))
        self._spin_m_max.setValue(int(cfg.get("m_max", 100)))
        self._spin_m_step.setValue(int(cfg.get("m_step", 25)))
        self._spin_ft_max.setValue(int(cfg.get("ft_max", 300)))
        self._spin_ft_step.setValue(int(cfg.get("ft_step", 50)))

    # ------------------------------------------------------------------
    # Message display
    # ------------------------------------------------------------------

    def _show_message(self, title: str, text: str, level: int) -> None:
        try:
            if self._iface:
                from qgis.core import Qgis
                self._iface.messageBar().pushMessage(
                    title, text, level=level, duration=4
                )
        except Exception:
            pass
