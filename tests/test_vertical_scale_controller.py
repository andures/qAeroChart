# tests/test_vertical_scale_controller.py
"""
Unit tests for VerticalScaleController.

Follows the same test pattern as test_profile_controller.py:
QObject/pyqtSignal are stubbed via qgis_mock, so no real Qt install needed.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock

import tests.mocks.qgis_mock  # noqa: F401

from qAeroChart.core.vertical_scale_controller import VerticalScaleController
from qAeroChart.core.vertical_scale_manager import VerticalScaleManager

_SUCCESS = 3
_INFO = 0
_CRITICAL = 2

SAMPLE_PARAMS: dict = {
    "name": "Test Scale",
    "angle": 90.0,
    "basepoint": {"x": 100.0, "y": 200.0},
    "scale_denominator": 10000,
    "tick_len": 15.0,
    "m_max": 100,
    "m_step": 25,
    "ft_max": 300,
    "ft_step": 50,
}


@pytest.fixture()
def mock_mgr() -> MagicMock:
    m = MagicMock(spec=VerticalScaleManager)
    m.get_all.return_value = []
    m.save_new.return_value = "vscale_abc12345"
    m.rename.return_value = True
    m.delete.return_value = True
    return m


@pytest.fixture()
def mock_lm() -> MagicMock:
    lm = MagicMock()
    lm.create_vertical_scale_run.return_value = (MagicMock(), MagicMock())
    return lm


@pytest.fixture()
def ctrl(mock_mgr: MagicMock) -> VerticalScaleController:
    return VerticalScaleController(mock_mgr)


@pytest.fixture()
def ctrl_with_lm(mock_mgr: MagicMock, mock_lm: MagicMock) -> VerticalScaleController:
    return VerticalScaleController(mock_mgr, mock_lm)


# ---------------------------------------------------------------------------
# get_all_scales
# ---------------------------------------------------------------------------

class TestGetAllScales:
    def test_delegates_to_manager(
        self, ctrl: VerticalScaleController, mock_mgr: MagicMock
    ) -> None:
        mock_mgr.get_all.return_value = [{"id": "x", "name": "A"}]
        result = ctrl.get_all_scales()
        mock_mgr.get_all.assert_called_once()
        assert result == [{"id": "x", "name": "A"}]


# ---------------------------------------------------------------------------
# run_scale
# ---------------------------------------------------------------------------

class TestRunScale:
    def test_calls_layer_manager_when_present(
        self, ctrl_with_lm: VerticalScaleController, mock_lm: MagicMock
    ) -> None:
        ctrl_with_lm.run_scale(SAMPLE_PARAMS)
        mock_lm.create_vertical_scale_run.assert_called_once()

    def test_persists_via_manager(
        self, ctrl_with_lm: VerticalScaleController, mock_mgr: MagicMock
    ) -> None:
        ctrl_with_lm.run_scale(SAMPLE_PARAMS)
        mock_mgr.save_new.assert_called_once_with(SAMPLE_PARAMS)

    def test_returns_true_on_success(
        self, ctrl_with_lm: VerticalScaleController
    ) -> None:
        assert ctrl_with_lm.run_scale(SAMPLE_PARAMS) is True

    def test_returns_false_without_layer_manager(
        self, ctrl: VerticalScaleController
    ) -> None:
        """No layer manager → cannot draw → returns False."""
        assert ctrl.run_scale(SAMPLE_PARAMS) is False

    def test_emits_scales_changed_on_success(
        self, ctrl_with_lm: VerticalScaleController
    ) -> None:
        fired: list = []
        ctrl_with_lm.scales_changed.connect(lambda: fired.append(True))
        ctrl_with_lm.run_scale(SAMPLE_PARAMS)
        assert len(fired) == 1

    def test_emits_message_on_success(
        self, ctrl_with_lm: VerticalScaleController
    ) -> None:
        messages: list = []
        ctrl_with_lm.message.connect(lambda t, m, l: messages.append((t, m, l)))
        ctrl_with_lm.run_scale(SAMPLE_PARAMS)
        assert len(messages) == 1
        _, _, level = messages[0]
        assert level == _SUCCESS

    def test_emits_critical_message_on_layer_error(
        self, ctrl_with_lm: VerticalScaleController, mock_lm: MagicMock
    ) -> None:
        mock_lm.create_vertical_scale_run.side_effect = RuntimeError("oops")
        messages: list = []
        ctrl_with_lm.message.connect(lambda t, m, l: messages.append((t, m, l)))
        result = ctrl_with_lm.run_scale(SAMPLE_PARAMS)
        assert result is False
        assert messages and messages[-1][2] == _CRITICAL

    def test_passes_name_to_layer_manager(
        self, ctrl_with_lm: VerticalScaleController, mock_lm: MagicMock
    ) -> None:
        ctrl_with_lm.run_scale({**SAMPLE_PARAMS, "name": "My VScale"})
        call_kwargs = mock_lm.create_vertical_scale_run.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("name") == "My VScale" or (
            len(call_kwargs.args) > 0 and call_kwargs.args[0] == "My VScale"
        )


# ---------------------------------------------------------------------------
# rename_scale
# ---------------------------------------------------------------------------

class TestRenameScale:
    def test_delegates_rename_to_manager(
        self, ctrl: VerticalScaleController, mock_mgr: MagicMock
    ) -> None:
        ctrl.rename_scale("vscale_001", "New Name")
        mock_mgr.rename.assert_called_once_with("vscale_001", "New Name")

    def test_returns_true_on_success(self, ctrl: VerticalScaleController) -> None:
        assert ctrl.rename_scale("vscale_001", "New") is True

    def test_emits_scales_changed(self, ctrl: VerticalScaleController) -> None:
        fired: list = []
        ctrl.scales_changed.connect(lambda: fired.append(True))
        ctrl.rename_scale("vscale_001", "New")
        assert len(fired) == 1

    def test_returns_false_when_manager_returns_false(
        self, ctrl: VerticalScaleController, mock_mgr: MagicMock
    ) -> None:
        mock_mgr.rename.return_value = False
        assert ctrl.rename_scale("bad_id", "X") is False


# ---------------------------------------------------------------------------
# delete_scale
# ---------------------------------------------------------------------------

class TestDeleteScale:
    def test_delegates_delete_to_manager(
        self, ctrl: VerticalScaleController, mock_mgr: MagicMock
    ) -> None:
        ctrl.delete_scale("vscale_001")
        mock_mgr.delete.assert_called_once_with("vscale_001")

    def test_returns_true_on_success(self, ctrl: VerticalScaleController) -> None:
        assert ctrl.delete_scale("vscale_001") is True

    def test_emits_scales_changed(self, ctrl: VerticalScaleController) -> None:
        fired: list = []
        ctrl.scales_changed.connect(lambda: fired.append(True))
        ctrl.delete_scale("vscale_001")
        assert len(fired) == 1

    def test_returns_false_when_not_found(
        self, ctrl: VerticalScaleController, mock_mgr: MagicMock
    ) -> None:
        mock_mgr.delete.return_value = False
        assert ctrl.delete_scale("no_such") is False
