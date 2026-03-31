"""Minimal QGIS stubs for unit testing without a running QGIS instance."""
from unittest.mock import MagicMock
import sys


class _QgsPointXY:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self._x = float(x)
        self._y = float(y)

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y

    def __eq__(self, other) -> bool:
        return isinstance(other, _QgsPointXY) and self._x == other._x and self._y == other._y

    def __repr__(self) -> str:
        return f"QgsPointXY({self._x}, {self._y})"


# ---------------------------------------------------------------------------
# PyQt stubs — allow "class Foo(QObject)" to work without a real Qt install
# ---------------------------------------------------------------------------

class _SignalInstance:
    """Per-object signal — tracks connect() and emit() calls in tests."""

    def __init__(self) -> None:
        self._slots: list = []
        self.emissions: list[tuple] = []

    def connect(self, slot) -> None:
        self._slots.append(slot)

    def emit(self, *args) -> None:
        self.emissions.append(args)
        for slot in self._slots:
            slot(*args)

    def disconnect(self, slot=None) -> None:
        if slot is not None:
            self._slots = [s for s in self._slots if s is not slot]
        else:
            self._slots.clear()


class _SignalDescriptor:
    """Descriptor produced by pyqtSignal() — gives each QObject instance its own _SignalInstance."""

    def __set_name__(self, owner, name: str) -> None:
        self._storage = f"_sig_{name}"

    def __get__(self, obj, objtype=None) -> "_SignalInstance":
        if obj is None:
            return self  # type: ignore[return-value]
        if not hasattr(obj, self._storage):
            setattr(obj, self._storage, _SignalInstance())
        return getattr(obj, self._storage)


def _pyqtSignal(*types) -> _SignalDescriptor:
    """Drop-in replacement for PyQt5 pyqtSignal(*types)."""
    return _SignalDescriptor()


class _QObject:
    """Minimal QObject base for testing (no real Qt event loop needed)."""
    def __init__(self, *args, **kwargs) -> None:
        pass


# ---------------------------------------------------------------------------
# Build mock qgis.core
# ---------------------------------------------------------------------------

qgis_core = MagicMock()
qgis_core.QgsPointXY = _QgsPointXY

# Qgis message level constants used by ProfileController / VerticalScaleController.
# Use a plain namespace instead of MagicMock so that missing attributes like
# ``MessageLevel`` resolve to ``AttributeError`` (not auto-generated mocks).
class _QgisMock:
    """Minimal QGIS 3-style Qgis namespace (no MessageLevel sub-enum)."""
    Info = 0
    Warning = 1
    Critical = 2
    Success = 3

qgis_core.Qgis = _QgisMock

# Patch sys.modules so any "from qgis.core import ..." resolves to our stubs
sys.modules.setdefault("qgis", MagicMock())
sys.modules["qgis.core"] = qgis_core

# Build a real PyQt QtCore mock with our stubs
_qtcore_mock = MagicMock()
_qtcore_mock.QObject = _QObject
_qtcore_mock.pyqtSignal = _pyqtSignal

sys.modules.setdefault("qgis.PyQt", MagicMock())
sys.modules["qgis.PyQt.QtCore"] = _qtcore_mock
sys.modules.setdefault("qgis.PyQt.QtGui", MagicMock())
sys.modules.setdefault("qgis.PyQt.QtWidgets", MagicMock())
sys.modules.setdefault("qgis.utils", MagicMock())
