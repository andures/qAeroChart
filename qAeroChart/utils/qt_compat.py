"""
Compatibility shim that normalises PyQt5 / PyQt6 API differences.

QGIS ships PyQt5 via ``qgis.PyQt``.  When running outside QGIS (dev/test)
PyQt6 may be available.  This module re-exports Qt enum values under a
unified API so plugin code never needs ``if PyQt5 / elif PyQt6`` guards.

Usage::

    from qAeroChart.utils.qt_compat import Qt, QMessageBox, QAbstractItemView, QVariant
"""
from __future__ import annotations

try:
    # QGIS runtime — always uses its own PyQt5 wrapper
    from qgis.PyQt.QtCore import Qt as _Qt
    from qgis.PyQt.QtCore import QVariant as _QVariant
    from qgis.PyQt.QtGui import QColor as _QColor
    from qgis.PyQt.QtGui import QFont as _QFont
    from qgis.PyQt.QtWidgets import QMessageBox as _QMessageBox
    from qgis.PyQt.QtWidgets import QAbstractItemView as _QAbstractItemView
except ImportError:
    try:
        from PyQt6.QtCore import Qt as _Qt  # type: ignore[no-redef]
        from PyQt6.QtGui import QColor as _QColor  # type: ignore[no-redef]
        from PyQt6.QtGui import QFont as _QFont  # type: ignore[no-redef]
        from PyQt6.QtWidgets import QMessageBox as _QMessageBox  # type: ignore[no-redef]
        from PyQt6.QtWidgets import QAbstractItemView as _QAbstractItemView  # type: ignore[no-redef]

        # PyQt6 removed QVariant from Python bindings; provide integer stubs
        # that match the C++ QMetaType values QGIS maps internally.
        class _QVariant:  # type: ignore[no-redef]
            Int = 2
            Double = 6
            String = 10
            Bool = 1
    except ImportError:
        from PyQt5.QtCore import Qt as _Qt  # type: ignore[no-redef]
        from PyQt5.QtCore import QVariant as _QVariant  # type: ignore[no-redef]
        from PyQt5.QtGui import QColor as _QColor  # type: ignore[no-redef]
        from PyQt5.QtGui import QFont as _QFont  # type: ignore[no-redef]
        from PyQt5.QtWidgets import QMessageBox as _QMessageBox  # type: ignore[no-redef]
        from PyQt5.QtWidgets import QAbstractItemView as _QAbstractItemView  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Qt namespace
# ---------------------------------------------------------------------------

class _QtCompat:
    """Normalised Qt namespace.

    In PyQt6 many constants moved into sub-enums (e.g. ``Qt.AlignmentFlag.AlignLeft``).
    This class exposes them under the PyQt5-compatible short names so the rest
    of the plugin code never needs to branch on the binding version.
    """

    # Item roles ---------------------------------------------------------------
    UserRole = getattr(_Qt, "UserRole", None) or _Qt.ItemDataRole.UserRole

    # Item flags ---------------------------------------------------------------
    ItemIsSelectable = (
        getattr(_Qt, "ItemIsSelectable", None)
        or _Qt.ItemFlag.ItemIsSelectable
    )

    # Context menu policy -------------------------------------------------------
    CustomContextMenu = (
        getattr(_Qt, "CustomContextMenu", None)
        or _Qt.ContextMenuPolicy.CustomContextMenu
    )

    # Keyboard keys ------------------------------------------------------------
    Key_F2 = getattr(_Qt, "Key_F2", None) or _Qt.Key.Key_F2
    Key_Delete = getattr(_Qt, "Key_Delete", None) or _Qt.Key.Key_Delete

    # Mouse buttons ------------------------------------------------------------
    LeftButton = getattr(_Qt, "LeftButton", None) or _Qt.MouseButton.LeftButton

    # Cursor shapes ------------------------------------------------------------
    CrossCursor = getattr(_Qt, "CrossCursor", None) or _Qt.CursorShape.CrossCursor

    # Pen cap and join styles --------------------------------------------------
    FlatCap = getattr(_Qt, "FlatCap", None) or _Qt.PenCapStyle.FlatCap
    MiterJoin = getattr(_Qt, "MiterJoin", None) or _Qt.PenJoinStyle.MiterJoin


Qt = _QtCompat


# ---------------------------------------------------------------------------
# QMessageBox button constants + passthrough for the question() dialog
# ---------------------------------------------------------------------------

class _QMessageBoxCompat:
    """Normalised QMessageBox enum values.

    Also proxies ``question()`` so callers can use a single import for both
    the dialog call and the button-flag comparisons.
    """

    Yes = getattr(_QMessageBox, "Yes", None) or _QMessageBox.StandardButton.Yes
    No = getattr(_QMessageBox, "No", None) or _QMessageBox.StandardButton.No

    @staticmethod
    def question(parent, title: str, text: str, buttons=None, default=None):
        """Delegate to the real QMessageBox.question() static method."""
        return _QMessageBox.question(parent, title, text, buttons, default)


QMessageBox = _QMessageBoxCompat


# ---------------------------------------------------------------------------
# QAbstractItemView selection mode constants
# ---------------------------------------------------------------------------

class _QAbstractItemViewCompat:
    """Normalised QAbstractItemView enum values."""

    ExtendedSelection = (
        getattr(_QAbstractItemView, "ExtendedSelection", None)
        or _QAbstractItemView.SelectionMode.ExtendedSelection
    )


QAbstractItemView = _QAbstractItemViewCompat


# ---------------------------------------------------------------------------
# QVariant type codes
# ---------------------------------------------------------------------------

# In QGIS / PyQt5 this is the real QVariant class; in PyQt6 dev environments
# it is the integer-stub class defined above.  Either way the numeric values
# (Int=2, Double=6, String=10, Bool=1) are identical to what QgsField expects.

QVariant = _QVariant


# ---------------------------------------------------------------------------
# QColor / QFont — passthrough; same API in PyQt5 and PyQt6
# ---------------------------------------------------------------------------

QColor = _QColor
QFont = _QFont
