"""Tests for the draggable Procedure rows / Preview splitter (Issue #121).

The OCA/H Table Builder must let the user resize the "Procedure rows" table
against the "Preview" table by dragging, instead of both panels splitting a
fixed height evenly.

The dialog class cannot be instantiated under the QGIS mocks (its Qt base is
a MagicMock), so these tests verify the module-level wiring: that
``_build_ui`` places both panels in a vertical ``QSplitter`` and gives each
pane a minimum height. This guards against regressing back to two fixed
``stretch=1`` siblings in the root layout.
"""
from __future__ import annotations

import inspect

import tests.mocks.qgis_mock  # noqa: F401

import qAeroChart.ui.oca_h_dialog as oca_h
from qAeroChart.utils.qt_compat import Qt


def test_procedure_rows_and_preview_are_in_a_vertical_splitter():
    src = inspect.getsource(oca_h)
    assert "QtWidgets.QSplitter(Qt.Vertical)" in src
    assert "splitter.addWidget(data_grp)" in src
    assert "splitter.addWidget(preview_container)" in src


def test_panes_have_minimum_heights():
    src = inspect.getsource(oca_h)
    assert "setMinimumHeight(120)" in src
    assert "setMinimumHeight(80)" in src


def test_qt_compat_exposes_vertical():
    assert hasattr(Qt, "Vertical")
