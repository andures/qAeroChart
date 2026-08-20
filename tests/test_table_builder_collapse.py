"""Tests for the collapsible 'Layout placement' group box (Issue #122).

All four table-builder dialogs must build the Layout placement panel with a
``QgsCollapsibleGroupBox`` that starts collapsed and does not persist its
collapse state between sessions.

The dialog classes cannot be instantiated under the QGIS mocks (their Qt base
is a MagicMock), so these tests verify the module-level wiring: that the
widget is imported from ``qgis.gui`` and that ``_build_ui`` configures it as
collapsed. This guards against regressions back to a plain ``QGroupBox``.
"""
from __future__ import annotations

import inspect
import sys

import pytest

import tests.mocks.qgis_mock  # noqa: F401

import qAeroChart.ui.dist_alt_calculator_dialog as dist_alt
import qAeroChart.ui.distance_altitude_table_dialog as dat
import qAeroChart.ui.gs_rod_dialog as gs_rod
import qAeroChart.ui.oca_h_dialog as oca_h

_DIALOG_MODULES = [
    ("gs_rod", gs_rod),
    ("dist_alt_calculator", dist_alt),
    ("oca_h", oca_h),
    ("distance_altitude", dat),
]


@pytest.mark.parametrize("_name,mod", _DIALOG_MODULES, ids=[m[0] for m in _DIALOG_MODULES])
def test_layout_placement_uses_qgis_collapsible_group_box(_name, mod):
    """QgsCollapsibleGroupBox is imported from qgis.gui (not the fallback)."""
    assert mod.QgsCollapsibleGroupBox is sys.modules["qgis.gui"].QgsCollapsibleGroupBox


@pytest.mark.parametrize("_name,mod", _DIALOG_MODULES, ids=[m[0] for m in _DIALOG_MODULES])
def test_layout_placement_collapsed_by_default(_name, mod):
    """_build_ui creates the Layout placement box collapsed without saving state."""
    src = inspect.getsource(mod)
    assert 'QgsCollapsibleGroupBox("Layout placement")' in src
    assert "setCollapsed(True)" in src
    assert "setSaveCollapsedState(False)" in src
    assert 'QtWidgets.QGroupBox("Layout placement")' not in src
