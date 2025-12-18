# -*- coding: utf-8 -*-
"""
Vertical Scale dialog: collects parameters and invokes the vertical scale generator.
"""
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialogButtonBox,
    QDoubleSpinBox,
    QSpinBox,
)
from qgis.PyQt.QtCore import Qt
from qgis.utils import iface
from .scripts.Vertical_Scale import run_vertical_scale


class VerticalScaleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.setWindowTitle("Vertical Scale")
        self.setMinimumWidth(320)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        # Scale denominator
        layout.addLayout(self._labeled_spin("Scale denominator (1:n)", "scale", 1000, 100000, 10000, step=500))
        # Offset
        layout.addLayout(self._labeled_dspin("Offset from guide line", "offset", -5000.0, 5000.0, -50.0, step=5.0))
        # Tick length
        layout.addLayout(self._labeled_dspin("Tick length", "tick", 1.0, 200.0, 15.0, step=1.0))
        # Meters
        layout.addLayout(self._labeled_spin("Meters max", "m_max", 10, 10000, 100, step=5))
        layout.addLayout(self._labeled_spin("Meters step", "m_step", 1, 1000, 25, step=1))
        # Feet
        layout.addLayout(self._labeled_spin("Feet max", "ft_max", 10, 50000, 300, step=10))
        layout.addLayout(self._labeled_spin("Feet step", "ft_step", 1, 5000, 50, step=5))

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _labeled_spin(self, text, attr, minv, maxv, default, step=1):
        box = QSpinBox()
        box.setRange(minv, maxv)
        box.setSingleStep(step)
        box.setValue(default)
        setattr(self, f"spin_{attr}", box)
        row = QHBoxLayout()
        row.addWidget(QLabel(text))
        row.addStretch(1)
        row.addWidget(box)
        return row

    def _labeled_dspin(self, text, attr, minv, maxv, default, step=1.0):
        box = QDoubleSpinBox()
        box.setRange(minv, maxv)
        box.setDecimals(2)
        box.setSingleStep(step)
        box.setValue(default)
        setattr(self, f"dspin_{attr}", box)
        row = QHBoxLayout()
        row.addWidget(QLabel(text))
        row.addStretch(1)
        row.addWidget(box)
        return row

    def _on_accept(self):
        try:
            run_vertical_scale(
                scale_denominator=float(self.spin_scale.value()),
                offset=float(self.dspin_offset.value()),
                tick_len=float(self.dspin_tick.value()),
                m_max=int(self.spin_m_max.value()),
                m_step=int(self.spin_m_step.value()),
                ft_max=int(self.spin_ft_max.value()),
                ft_step=int(self.spin_ft_step.value()),
            )
            self.accept()
        except Exception as e:
            try:
                iface.messageBar().pushCritical("Vertical Scale", f"Error creating scale: {e}")
            except Exception:
                print(f"Vertical Scale ERROR: {e}")
            self.reject()
