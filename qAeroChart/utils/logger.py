# -*- coding: utf-8 -*-
"""
logger.py - Central logging utility for qAeroChart.

Routes messages to QgsMessageLog when running inside QGIS, and falls back to
print() when the QGIS runtime is unavailable (e.g., unit tests).
"""
from __future__ import annotations

_TAG = "qAeroChart"


def log(msg: str, level: str = "INFO") -> None:
    """
    Log a message to QgsMessageLog with a fallback to print().

    Args:
        msg: The message text.
        level: Severity — "INFO", "WARNING", or "CRITICAL".
    """
    try:
        from qgis.core import QgsMessageLog, Qgis
        qgis_level = {
            "INFO": Qgis.Info,
            "WARNING": Qgis.Warning,
            "CRITICAL": Qgis.Critical,
        }.get(level.upper(), Qgis.Info)
        QgsMessageLog.logMessage(msg, _TAG, qgis_level)
    except Exception:
        print(f"[{_TAG}] {level.upper()}: {msg}")
