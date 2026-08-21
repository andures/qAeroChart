# -*- coding: utf-8 -*-
"""MSA (Minimum Sector Altitude) donut/sector dock widget — mirrors
HoldingDockWidget / VerticalScaleDockWidget (Issue #104).

Ported from a standalone QGIS console script into the plugin's dock
architecture: geometry math lives in ``core/msa.py`` (pure Python, unit
tested), layer creation/styling/labeling in ``core/msa_layer_manager.py``
(QGIS-dependent), and this class only handles UI + signal wiring.
"""
from __future__ import annotations

try:
    from qgis.PyQt import QtWidgets
except ImportError:
    try:
        from PyQt6 import QtWidgets  # type: ignore
    except ImportError:
        from PyQt5 import QtWidgets  # type: ignore

from qgis.core import QgsProject
from qgis.utils import iface

from .utils.qt_compat import (
    Qt,
    QAbstractItemView,
    QEvent,
    QHeaderView,
    QSignalBlocker,
    QStyledItemDelegate,
    MsgLevel,
)
from .utils.validators import Validators
from .core.msa import MSASector, build_msa_sectors
from .core.msa_layer_manager import MsaLayerManager

# QEvent.Type nesting differs across PyQt5/6 point releases — resolve once.
_EVT_FOCUS_IN = getattr(QEvent, "FocusIn", None) or QEvent.Type.FocusIn
_EVT_SHOW = getattr(QEvent, "Show", None) or QEvent.Type.Show

# ---------------------------------------------------------------------------
# QGIS 3 / 4 compatibility for the Point geometry-type enum (same idiom as
# tools/profile_point_tool.py — not centralized in qt_compat, see Issue #104
# plan notes).
# ---------------------------------------------------------------------------
try:
    from qgis.core import Qgis as _Qgis
    _GEOM_POINT = _Qgis.GeometryType.Point
except AttributeError:
    from qgis.core import QgsWkbTypes as _QgsWkbTypes
    _GEOM_POINT = _QgsWkbTypes.PointGeometry


class SectorSpinBoxDelegate(QStyledItemDelegate):
    """Select-all-on-edit QDoubleSpinBox delegate for the sectors table."""

    COL_RANGES = {
        0: (0.0, 360.0, 1),     # Start Brg
        1: (0.0, 360.0, 1),     # End Brg
        2: (0.0, 150.0, 1),     # Inner Rad
        3: (0.0, 150.0, 1),     # Outer Rad
        4: (0.0, 60000.0, 0),   # Altitude
    }

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QDoubleSpinBox(parent)
        minv, maxv, decimals = self.COL_RANGES.get(index.column(), (0.0, 999.0, 1))
        editor.setRange(minv, maxv)
        editor.setDecimals(decimals)
        if index.column() == 4:
            editor.setSingleStep(100.0)
        return editor

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.EditRole)
        if val is not None:
            editor.setValue(float(val))

    def setModelData(self, editor, model, index):
        editor.interpretText()
        model.setData(index, editor.value(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def eventFilter(self, editor, event):
        if event.type() in (_EVT_FOCUS_IN, _EVT_SHOW):
            editor.selectAll()
        return super().eventFilter(editor, event)


class MSADockWidget(QtWidgets.QDockWidget):
    """Dock widget for creating MSA donut/sector figures (Issue #104)."""

    COLUMN_LABELS = [
        "Start Brg (°)", "End Brg (°)", "Inner Rad (NM)", "Outer Rad (NM)", "Altitude (ft)",
    ]

    # preset index -> list of (start_brg, end_brg, inner_r_nm, outer_r_nm, altitude_ft)
    PRESETS = {
        1: [(0, 360, 0, 25, 3000)],
        2: [(0, 180, 0, 25, 3000), (180, 360, 0, 25, 4500)],
        3: [(0, 120, 0, 25, 3000), (120, 240, 0, 25, 3800), (240, 360, 0, 25, 4500)],
        4: [(0, 90, 0, 25, 2500), (90, 180, 0, 25, 3000), (180, 270, 0, 25, 4200), (270, 360, 0, 25, 3800)],
    }

    def __init__(self, parent=None):
        _fallback = iface.mainWindow() if iface else None
        super().__init__(parent or _fallback)
        self.setWindowTitle("MSA Sector Generator")
        self.setObjectName("MsaDock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self._layer_manager = MsaLayerManager()
        self._monitored_layer = None
        self._preview_layer = None
        self._signals_connected = False
        # (source_layer_id, feature_id) -> msa_id, so committing again for the same
        # point feature replaces its figure instead of piling up a duplicate.
        self._committed_by_feature: dict[tuple, str] = {}

        self._build_ui()
        self.combo_preset.setCurrentIndex(4)  # triggers apply_preset via signal

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        container = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Quick Preset:"))
        self.combo_preset = QtWidgets.QComboBox()
        self.combo_preset.addItems([
            "Custom", "Single Circle (25 NM)", "2 Sectors (180°)",
            "3 Sectors (120°)", "4 Quadrants (90°)",
        ])
        preset_row.addWidget(self.combo_preset)
        self.chk_preview = QtWidgets.QCheckBox("Enable Live Preview")
        self.chk_preview.setChecked(True)
        preset_row.addWidget(self.chk_preview)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        self.lbl_status = QtWidgets.QLabel("Select a point feature on canvas.")
        self.lbl_status.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        ref_group = QtWidgets.QGroupBox("Bearing Reference System")
        ref_layout = QtWidgets.QVBoxLayout(ref_group)

        north_row = QtWidgets.QHBoxLayout()
        self.radio_mag = QtWidgets.QRadioButton("Magnetic North")
        self.radio_true = QtWidgets.QRadioButton("True North")
        self.radio_mag.setChecked(True)
        self._north_group = QtWidgets.QButtonGroup(self)
        self._north_group.addButton(self.radio_mag)
        self._north_group.addButton(self.radio_true)
        north_row.addWidget(self.radio_mag)
        north_row.addWidget(self.radio_true)
        north_row.addStretch()
        ref_layout.addLayout(north_row)

        self.magvar_container = QtWidgets.QWidget()
        magvar_row = QtWidgets.QHBoxLayout(self.magvar_container)
        magvar_row.setContentsMargins(0, 4, 0, 4)
        magvar_row.addWidget(QtWidgets.QLabel("Mag Var:"))
        self.spin_magvar = QtWidgets.QDoubleSpinBox()
        self.spin_magvar.setRange(0.0, 180.0)
        self.spin_magvar.setDecimals(2)
        magvar_row.addWidget(self.spin_magvar)
        self.radio_east = QtWidgets.QRadioButton("E")
        self.radio_west = QtWidgets.QRadioButton("W")
        self.radio_east.setChecked(True)
        self._ew_group = QtWidgets.QButtonGroup(self)
        self._ew_group.addButton(self.radio_east)
        self._ew_group.addButton(self.radio_west)
        magvar_row.addWidget(self.radio_east)
        magvar_row.addWidget(self.radio_west)
        magvar_row.addStretch()
        ref_layout.addWidget(self.magvar_container)

        dir_row = QtWidgets.QHBoxLayout()
        dir_row.addWidget(QtWidgets.QLabel("Bearing Convention:"))
        self.combo_dir = QtWidgets.QComboBox()
        self.combo_dir.addItems([
            "Bearings FROM Station (Outbound)", "Bearings TO Station (Inbound)",
        ])
        dir_row.addWidget(self.combo_dir)
        dir_row.addStretch()
        ref_layout.addLayout(dir_row)

        layout.addWidget(ref_group)

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(self.COLUMN_LABELS)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.AnyKeyPressed
            | QAbstractItemView.EditKeyPressed
        )
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setItemDelegate(SectorSpinBoxDelegate(self.table))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        row_btns = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Sector / Ring")
        self.btn_remove = QtWidgets.QPushButton("Remove Selected")
        row_btns.addWidget(self.btn_add)
        row_btns.addWidget(self.btn_remove)
        row_btns.addStretch()
        layout.addLayout(row_btns)

        self.btn_generate = QtWidgets.QPushButton("Commit MSA Layer to Map")
        self.btn_generate.setStyleSheet(
            "font-weight: bold; background-color: #00557f; color: white; padding: 8px;"
        )
        layout.addWidget(self.btn_generate)

        self.setWidget(container)
        self._connect_ui_signals()

    def _connect_ui_signals(self):
        self.combo_preset.currentIndexChanged.connect(self.apply_preset)
        self.radio_mag.toggled.connect(self._toggle_magvar_visibility)
        self.radio_mag.toggled.connect(self.update_live_preview)
        self.spin_magvar.valueChanged.connect(self.update_live_preview)
        self.radio_east.toggled.connect(self.update_live_preview)
        self.combo_dir.currentIndexChanged.connect(self.update_live_preview)
        self.table.itemChanged.connect(self.update_live_preview)
        self.btn_add.clicked.connect(lambda: self.add_sector_row())
        self.btn_remove.clicked.connect(self._remove_selected_row)
        self.chk_preview.toggled.connect(self._on_preview_toggled)
        self.btn_generate.clicked.connect(self.generate_final_layer)

    # ------------------------------------------------------------------
    # Dock lifecycle — canvas/layer signals connect only while the dock is
    # visible, instead of leaking updates in the background while hidden.
    # ------------------------------------------------------------------

    def showEvent(self, event):
        self._connect_canvas_signals()
        self.update_live_preview()
        super().showEvent(event)

    def hideEvent(self, event):
        self._disconnect_canvas_signals()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._disconnect_canvas_signals()
        self._clear_preview_layer()
        super().closeEvent(event)

    def _connect_canvas_signals(self):
        if self._signals_connected:
            return
        canvas = iface.mapCanvas()
        canvas.selectionChanged.connect(self.update_live_preview)
        canvas.extentsChanged.connect(self.update_live_preview)
        iface.currentLayerChanged.connect(self._on_current_layer_changed)
        self._setup_layer_connections(iface.activeLayer())
        self._signals_connected = True

    def _disconnect_canvas_signals(self):
        if not self._signals_connected:
            return
        canvas = iface.mapCanvas()
        try:
            canvas.selectionChanged.disconnect(self.update_live_preview)
            canvas.extentsChanged.disconnect(self.update_live_preview)
            iface.currentLayerChanged.disconnect(self._on_current_layer_changed)
        except Exception:  # nosec B110 - best-effort cleanup; a stale/already-cleared state is harmless
            pass
        self._setup_layer_connections(None)
        self._signals_connected = False

    def _setup_layer_connections(self, layer):
        # The whole body is wrapped: during QGIS application shutdown, layers
        # and the canvas can be torn down out of order relative to pending
        # Qt signals, so *any* sip-wrapped object touched here — the stored
        # `self._monitored_layer` or the freshly-signal-provided `layer` —
        # may already be a dead C++ object. `is not None` (identity check)
        # never touches the wrapped object; a plain truthiness check does,
        # and raises RuntimeError("wrapped C/C++ object ... has been
        # deleted"). Best-effort: if this fires, there is nothing left to
        # clean up anyway.
        try:
            if self._monitored_layer is not None:
                try:
                    self._monitored_layer.geometryChanged.disconnect(self.update_live_preview)
                    self._monitored_layer.featureDeleted.disconnect(self.update_live_preview)
                except Exception:  # nosec B110 - best-effort cleanup; a stale/already-cleared state is harmless
                    pass
                self._monitored_layer = None

            if layer is not None and layer.type() == layer.VectorLayer:
                self._monitored_layer = layer
                try:
                    layer.geometryChanged.connect(self.update_live_preview)
                    layer.featureDeleted.connect(self.update_live_preview)
                except Exception:  # nosec B110 - best-effort cleanup; a stale/already-cleared state is harmless
                    pass
        except RuntimeError:
            self._monitored_layer = None

    def _on_current_layer_changed(self, layer):
        self._setup_layer_connections(layer)
        self.update_live_preview()

    def _toggle_magvar_visibility(self, is_magnetic_checked):
        self.magvar_container.setVisible(is_magnetic_checked)

    def _on_preview_toggled(self, checked):
        if checked:
            self.update_live_preview()
        else:
            self._clear_preview_layer()

    # ------------------------------------------------------------------
    # Table rows / presets
    # ------------------------------------------------------------------

    def add_sector_row(self, start_brg=0.0, end_brg=360.0, inner_r=0.0, outer_r=25.0, alt=2500.0):
        row = self.table.rowCount()
        blocker = QSignalBlocker(self.table)
        self.table.insertRow(row)
        for col, val in enumerate((start_brg, end_brg, inner_r, outer_r, alt)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(Qt.EditRole, float(val))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)
        del blocker
        self.update_live_preview()

    def _remove_selected_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.update_live_preview()

    def apply_preset(self, index):
        blocker = QSignalBlocker(self.table)
        self.table.setRowCount(0)
        for start, end, inner, outer, alt in self.PRESETS.get(index, []):
            self.add_sector_row(start, end, inner, outer, alt)
        del blocker
        self.update_live_preview()

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def _collect_sectors(self) -> list[MSASector]:
        sectors = []
        for row in range(self.table.rowCount()):
            items = [self.table.item(row, col) for col in range(5)]
            if not all(items):
                continue
            values = [float(item.data(Qt.EditRole) or 0.0) for item in items]
            sectors.append(MSASector(*values))
        return sectors

    def _bearing_context(self):
        is_magnetic = self.radio_mag.isChecked()
        is_west = self.radio_west.isChecked()
        mag_var_signed = -self.spin_magvar.value() if is_west else self.spin_magvar.value()
        is_inbound = "TO" in self.combo_dir.currentText()
        ref_north_str = "MAG" if is_magnetic else "TRUE"
        brg_type_str = "INBOUND" if is_inbound else "OUTBOUND"
        return is_magnetic, mag_var_signed, is_inbound, ref_north_str, brg_type_str

    def _active_point_feature(self):
        """Return (layer, feature) for the single selected point feature, or (None, None).

        Requires exactly one selected feature (matches ``holding_dock.py``'s
        ``_pick_fix_from_line`` convention: ``selectedFeatureCount() != 1``),
        instead of silently taking the first of a possibly-larger selection.
        """
        layer = iface.activeLayer()
        if not layer or layer.geometryType() != _GEOM_POINT:
            self.lbl_status.setText("Active layer in Layers Panel must be a Point layer.")
            self.lbl_status.setStyleSheet("color: #d9534f; font-weight: bold;")
            return None, None

        count = layer.selectedFeatureCount()
        if count == 0:
            self.lbl_status.setText(f"Layer '{layer.name()}' active. Click a point feature to select it.")
            self.lbl_status.setStyleSheet("color: #f0ad4e; font-weight: bold;")
            return None, None
        if count > 1:
            self.lbl_status.setText(f"Select exactly one point feature in '{layer.name()}' (currently {count}).")
            self.lbl_status.setStyleSheet("color: #f0ad4e; font-weight: bold;")
            return None, None

        feature = layer.selectedFeatures()[0]
        self.lbl_status.setText(f"Previewing center on feature ID: {feature.id()} ({layer.name()})")
        self.lbl_status.setStyleSheet("color: #5cb85c; font-weight: bold;")
        return layer, feature

    # ------------------------------------------------------------------
    # Live preview
    # ------------------------------------------------------------------

    def update_live_preview(self):
        if not self.chk_preview.isChecked():
            return

        # Invoked reactively from canvas/layer Qt signals, so it can run
        # during QGIS application shutdown, when layers/canvas are being torn
        # down out of order — any sip-wrapped object touched below may
        # already be a dead C++ object (see _setup_layer_connections). Best
        # effort: if that happens mid-preview-update, there is nothing useful
        # left to draw or clean up.
        try:
            _layer, feature = self._active_point_feature()
            if not feature:
                self._clear_preview_layer()
                return

            center = feature.geometry().asPoint()
            is_magnetic, mag_var_signed, is_inbound, ref_north_str, brg_type_str = self._bearing_context()
            sector_geoms = build_msa_sectors(
                center.x(), center.y(), self._collect_sectors(),
                is_magnetic=is_magnetic, mag_var_signed=mag_var_signed, is_inbound=is_inbound,
            )

            self._preview_layer = self._layer_manager.get_or_create_preview_layer(iface)
            self._layer_manager.replace_preview(
                self._preview_layer, sector_geoms,
                brg_type_str=brg_type_str, ref_north_str=ref_north_str, mag_var_signed=mag_var_signed,
            )
            iface.mapCanvas().refresh()
        except RuntimeError:
            pass

    def _clear_preview_layer(self):
        # Same sip-staleness hazard as _setup_layer_connections: `is not None`
        # avoids touching the wrapped object, and the id()/clear_preview calls
        # are guarded in case the preview layer was deleted from the project
        # (e.g. manually removed in the Layers panel) since we last stored it.
        if self._preview_layer is not None:
            try:
                if QgsProject.instance().mapLayer(self._preview_layer.id()):
                    self._layer_manager.clear_preview(self._preview_layer)
            except RuntimeError:
                pass  # underlying preview layer object was deleted
            self._preview_layer = None
        iface.mapCanvas().refresh()

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    def generate_final_layer(self):
        source_layer, feature = self._active_point_feature()
        if not feature:
            iface.messageBar().pushMessage(
                "qAeroChart", "Select a point feature on the map first.",
                level=MsgLevel.Warning, duration=4,
            )
            return

        sectors = self._collect_sectors()
        if not sectors:
            iface.messageBar().pushMessage(
                "qAeroChart", "Add at least one sector/ring before committing.",
                level=MsgLevel.Warning, duration=4,
            )
            return

        row_errors = []
        for idx, sector in enumerate(sectors, start=1):
            is_valid, errors = Validators.validate_msa_sector(
                sector.start_brg, sector.end_brg, sector.inner_r_nm,
                sector.outer_r_nm, sector.altitude_ft,
            )
            if not is_valid:
                row_errors.append(f"Row {idx}: " + "; ".join(errors.values()))

        if row_errors:
            iface.messageBar().pushCritical("qAeroChart", " | ".join(row_errors))
            return

        center = feature.geometry().asPoint()
        is_magnetic, mag_var_signed, is_inbound, ref_north_str, brg_type_str = self._bearing_context()
        sector_geoms = build_msa_sectors(
            center.x(), center.y(), sectors,
            is_magnetic=is_magnetic, mag_var_signed=mag_var_signed, is_inbound=is_inbound,
        )

        layer = self._layer_manager.get_or_create_layer(iface)

        # Re-committing for the same point feature replaces its previous MSA
        # figure instead of duplicating it (mirrors HoldingLayerManager.remove_holding).
        feature_key = (source_layer.id(), feature.id())
        existing_msa_id = self._committed_by_feature.get(feature_key)
        if existing_msa_id:
            self._layer_manager.remove_sectors(layer, existing_msa_id)

        msa_id = self._layer_manager.add_sectors(
            layer, sector_geoms,
            brg_type_str=brg_type_str, ref_north_str=ref_north_str, mag_var_signed=mag_var_signed,
            msa_id=existing_msa_id,
        )
        self._committed_by_feature[feature_key] = msa_id
        iface.mapCanvas().refresh()
        iface.messageBar().pushMessage(
            "qAeroChart",
            f"MSA figure {'updated' if existing_msa_id else 'committed'} (id={msa_id}, {len(sectors)} sector(s)).",
            level=MsgLevel.Success, duration=5,
        )
