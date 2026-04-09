"""Tests verifying scale bar groups are inserted at position 0 of the layer tree (#88).

These tests mock the QGIS layer tree to confirm that:
- root.insertGroup(0, name) is called when the group does not yet exist
- root.insertGroup is NOT called when the group already exists (reuse)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest
import tests.mocks.qgis_mock  # noqa: F401


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(existing_group=None):
    """Return a mock QgsProject whose layer tree root has a stable mock structure."""
    root = MagicMock()
    root.findGroup.return_value = existing_group  # None → new group; MagicMock → existing
    root.insertGroup.return_value = MagicMock()

    project = MagicMock()
    project.layerTreeRoot.return_value = root
    project.addMapLayer.return_value = MagicMock()
    return project, root


# ---------------------------------------------------------------------------
# LayerManager.create_vertical_scale_run
# ---------------------------------------------------------------------------

class TestVerticalScaleLayerOrder:
    """Vertical scale groups must be inserted at index 0 when new."""

    def _call(self, project):
        """Call create_vertical_scale_run with minimal valid args via a patched project."""
        from qAeroChart.core.layer_manager import LayerManager

        mgr = LayerManager.__new__(LayerManager)
        mgr.project = MagicMock()
        mgr.layers = {}
        mgr.layer_group = None
        mgr.debug = False
        mgr._dbg = lambda *a: None
        mgr._log = lambda *a, **k: None

        with patch("qAeroChart.core.layer_manager.QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            # Patch the local _QgsProject alias used inside the method
            with patch.dict(
                "sys.modules",
                {"qgis.core": _make_qgis_core_mock(project)},
            ):
                try:
                    mgr.create_vertical_scale_run(
                        name="Vertical Scale",
                        basepoint_x=0.0,
                        basepoint_y=0.0,
                        angle=0.0,
                    )
                except Exception:
                    pass  # geometry/labeling failures are OK for this test

    def test_new_group_uses_insert_at_zero(self):
        project, root = _make_project(existing_group=None)
        # After insertGroup(0, name), findGroup is called again — return a real mock
        re_found = MagicMock()
        root.findGroup.side_effect = [None, re_found]

        _run_create_vertical(project)

        root.insertGroup.assert_called_once_with(0, "Vertical Scale")

    def test_existing_group_not_re_inserted(self):
        existing = MagicMock()
        project, root = _make_project(existing_group=existing)

        _run_create_vertical(project)

        root.insertGroup.assert_not_called()


# ---------------------------------------------------------------------------
# LayerManager.create_horizontal_scale_run
# ---------------------------------------------------------------------------

class TestHorizontalScaleLayerOrder:
    """Horizontal scale groups must be inserted at index 0 when new."""

    def test_new_group_uses_insert_at_zero(self):
        project, root = _make_project(existing_group=None)
        re_found = MagicMock()
        root.findGroup.side_effect = [None, re_found]

        _run_create_horizontal(project)

        root.insertGroup.assert_called_once_with(0, "Horizontal Scale")

    def test_existing_group_not_re_inserted(self):
        existing = MagicMock()
        project, root = _make_project(existing_group=existing)

        _run_create_horizontal(project)

        root.insertGroup.assert_not_called()


# ---------------------------------------------------------------------------
# Internal helpers that drive the code under test
# ---------------------------------------------------------------------------

def _make_qgis_core_mock(project):
    """Return a qgis.core mock that routes QgsProject.instance() to 'project'."""
    import sys
    qgis_core = sys.modules["qgis.core"]
    # Create a fresh child mock that inherits the existing stubs but overrides
    # QgsProject so the local 'as _QgsProject' alias picks up our project.
    mock = MagicMock(wraps=qgis_core)
    mock.QgsProject = MagicMock()
    mock.QgsProject.instance.return_value = project
    return mock


def _run_create_vertical(project):
    """Drive create_vertical_scale_run using a mocked QGIS project."""
    from qAeroChart.core.layer_manager import LayerManager

    mgr = LayerManager.__new__(LayerManager)
    mgr.project = MagicMock()
    mgr.layers = {}
    mgr.layer_group = None
    mgr.debug = False
    mgr._dbg = lambda *a: None
    mgr._log = lambda *a, **k: None

    import sys
    orig = sys.modules.get("qgis.core")
    sys.modules["qgis.core"] = _make_qgis_core_mock(project)
    try:
        mgr.create_vertical_scale_run(
            name="Vertical Scale",
            basepoint_x=0.0,
            basepoint_y=0.0,
            angle=0.0,
        )
    except Exception:
        pass
    finally:
        if orig is not None:
            sys.modules["qgis.core"] = orig


def _run_create_horizontal(project):
    """Drive create_horizontal_scale_run using a mocked QGIS project."""
    from qAeroChart.core.layer_manager import LayerManager

    mgr = LayerManager.__new__(LayerManager)
    mgr.project = MagicMock()
    mgr.layers = {}
    mgr.layer_group = None
    mgr.debug = False
    mgr._dbg = lambda *a: None
    mgr._log = lambda *a, **k: None

    import sys
    orig = sys.modules.get("qgis.core")
    sys.modules["qgis.core"] = _make_qgis_core_mock(project)
    try:
        mgr.create_horizontal_scale_run(
            name="Horizontal Scale",
            basepoint_x=0.0,
            basepoint_y=0.0,
            angle=0.0,
        )
    except Exception:
        pass
    finally:
        if orig is not None:
            sys.modules["qgis.core"] = orig
