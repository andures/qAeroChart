# -*- coding: utf-8 -*-
"""
VerticalScaleController — MVC mediator between VerticalScaleDockWidget and
VerticalScaleManager / LayerManager.

The dock widget must:
- Call controller methods for every write operation.
- Connect to ``message`` and ``scales_changed`` signals for UI updates.
- Never call VerticalScaleManager or LayerManager directly.
"""
from __future__ import annotations

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import Qgis

from .vertical_scale_manager import VerticalScaleManager
from .layer_manager import LayerManager
from ..utils.logger import log


class VerticalScaleController(QObject):
    """Mediator between VerticalScaleDockWidget, VerticalScaleManager, and LayerManager."""

    # (title, text, Qgis.MessageLevel int)
    message: pyqtSignal = pyqtSignal(str, str, int)
    # Emitted after any change to the persisted scale list
    scales_changed: pyqtSignal = pyqtSignal()

    def __init__(
        self,
        scale_manager: VerticalScaleManager,
        layer_manager: LayerManager | None = None,
    ) -> None:
        super().__init__()
        self._scale_manager = scale_manager
        self._layer_manager = layer_manager

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_all_scales(self) -> list[dict]:
        """Return lightweight metadata list from the manager."""
        return self._scale_manager.get_all()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def run_scale(self, params: dict) -> bool:
        """Draw a vertical scale on the map and persist the configuration.

        Requires a ``LayerManager`` — returns False immediately when none is set.
        """
        if self._layer_manager is None:
            log("VerticalScaleController.run_scale: no layer manager", "WARNING")
            return False

        try:
            bp = params.get("basepoint", {})
            self._layer_manager.create_vertical_scale_run(
                name=params.get("name", "Vertical Scale"),
                basepoint_x=float(bp.get("x", 0.0)),
                basepoint_y=float(bp.get("y", 0.0)),
                angle=float(params.get("angle", 90.0)),
                scale_denominator=float(params.get("scale_denominator", 10000.0)),
                offset=float(params.get("offset", -50.0)),
                tick_len=float(params.get("tick_len", 15.0)),
                m_max=int(params.get("m_max", 100)),
                m_step=int(params.get("m_step", 25)),
                ft_max=int(params.get("ft_max", 300)),
                ft_step=int(params.get("ft_step", 50)),
            )
            self._scale_manager.save_new(params)
            self.scales_changed.emit()
            self.message.emit(
                "Vertical Scale",
                f"Scale '{params.get('name', 'Vertical Scale')}' generated successfully.",
                Qgis.Success,
            )
            return True

        except Exception as e:
            log(f"VerticalScaleController.run_scale failed: {e}", "ERROR")
            self.message.emit("Vertical Scale Error", str(e), Qgis.Critical)
            return False

    def rename_scale(self, scale_id: str, new_name: str) -> bool:
        """Rename a persisted scale. Returns True on success."""
        try:
            result = self._scale_manager.rename(scale_id, new_name)
            if result:
                self.scales_changed.emit()
                self.message.emit(
                    "Vertical Scale",
                    f"Renamed to '{new_name}'.",
                    Qgis.Info,
                )
            return result
        except Exception as e:
            log(f"VerticalScaleController.rename_scale failed: {e}", "ERROR")
            self.message.emit("Vertical Scale Error", str(e), Qgis.Critical)
            return False

    def delete_scale(self, scale_id: str) -> bool:
        """Delete a persisted scale. Returns True when the id was found."""
        try:
            result = self._scale_manager.delete(scale_id)
            if result:
                self.scales_changed.emit()
                self.message.emit("Vertical Scale", "Scale deleted.", Qgis.Info)
            return result
        except Exception as e:
            log(f"VerticalScaleController.delete_scale failed: {e}", "ERROR")
            self.message.emit("Vertical Scale Error", str(e), Qgis.Critical)
            return False
