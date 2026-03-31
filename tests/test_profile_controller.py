# tests/test_profile_controller.py
"""
Unit tests for ProfileController.

QObject / pyqtSignal are stubbed in tests/mocks/qgis_mock.py so these tests
run without a real QGIS instance.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock

# QGIS stubs (sets up QObject, pyqtSignal, Qgis constants, etc.)
import tests.mocks.qgis_mock  # noqa: F401

from qAeroChart.core.profile_controller import ProfileController  # noqa: E402
from qAeroChart.core.profile_manager import ProfileManager  # noqa: E402
from qAeroChart.core.layout_manager import LayoutManager  # noqa: E402

# Convenience aliases for Qgis level constants (same values as the mock)
_SUCCESS = 3
_INFO = 0
_CRITICAL = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASIC_CONFIG: dict = {
    "version": "2.0",
    "origin_point": {"x": 1.0, "y": 2.0},
    "runway": {"direction": "07", "length": "3000", "thr_elevation": "13", "tch_rdh": "50"},
    "profile_points": [{"point_name": "MAPt", "distance_nm": "0.0", "elevation_ft": "500"}],
    "style": {"vertical_exaggeration": 10.0, "axis_max_nm": 12.0},
    "moca_segments": [],
    "oca": None,
    "oca_segments": [],
}


@pytest.fixture()
def mock_pm() -> MagicMock:
    """ProfileManager mock with sensible defaults."""
    pm = MagicMock(spec=ProfileManager)
    pm.get_all_profiles.return_value = []
    pm.get_profile.return_value = BASIC_CONFIG.copy()
    pm.get_profile_display_name.return_value = "Profile 07 – RWY07"
    return pm


@pytest.fixture()
def mock_lm() -> MagicMock:
    """LayerManager mock."""
    lm = MagicMock()
    lm.create_all_layers.return_value = {}
    lm.populate_layers_from_config.return_value = True
    return lm


@pytest.fixture()
def mock_layout_mgr() -> MagicMock:
    """LayoutManager mock."""
    return MagicMock(spec=LayoutManager)


@pytest.fixture()
def ctrl(mock_pm: MagicMock) -> ProfileController:
    return ProfileController(mock_pm)


@pytest.fixture()
def ctrl_with_lm(mock_pm: MagicMock, mock_lm: MagicMock) -> ProfileController:
    return ProfileController(mock_pm, mock_lm)


@pytest.fixture()
def ctrl_with_layout(mock_pm: MagicMock, mock_layout_mgr: MagicMock) -> ProfileController:
    return ProfileController(mock_pm, layout_manager=mock_layout_mgr)


# ---------------------------------------------------------------------------
# Read-only delegation tests
# ---------------------------------------------------------------------------


class TestReadOnly:
    def test_get_all_profiles_delegates(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        mock_pm.get_all_profiles.return_value = [{"id": "1"}]
        result = ctrl.get_all_profiles()
        mock_pm.get_all_profiles.assert_called_once()
        assert result == [{"id": "1"}]

    def test_get_profile_delegates(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        result = ctrl.get_profile("abc")
        mock_pm.get_profile.assert_called_once_with("abc")
        assert result == BASIC_CONFIG

    def test_get_profile_display_name_delegates(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        profile = {"id": "1", "name": "Profile 07"}
        result = ctrl.get_profile_display_name(profile)
        mock_pm.get_profile_display_name.assert_called_once_with(profile)
        assert result == "Profile 07 – RWY07"


# ---------------------------------------------------------------------------
# save_or_update_profile tests
# ---------------------------------------------------------------------------


class TestSaveOrUpdate:
    def test_new_profile_calls_save(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        ctrl.save_or_update_profile("Alpha", BASIC_CONFIG)
        mock_pm.save_profile.assert_called_once_with("Alpha", BASIC_CONFIG)
        mock_pm.update_profile.assert_not_called()

    def test_update_profile_calls_update(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        ctrl.save_or_update_profile("Alpha", BASIC_CONFIG, profile_id="id-001")
        mock_pm.update_profile.assert_called_once_with("id-001", "Alpha", BASIC_CONFIG)
        mock_pm.save_profile.assert_not_called()

    def test_returns_true_on_success(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        result = ctrl.save_or_update_profile("Alpha", BASIC_CONFIG)
        assert result is True

    def test_emits_message_on_success(self, ctrl: ProfileController) -> None:
        received: list[tuple] = []
        ctrl.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl.save_or_update_profile("Alpha", BASIC_CONFIG)
        assert len(received) == 1
        title, text, level = received[0]
        assert title == "Profile Saved"
        assert level == _SUCCESS

    def test_emits_profiles_changed_on_success(self, ctrl: ProfileController) -> None:
        fired: list[bool] = []
        ctrl.profiles_changed.connect(lambda: fired.append(True))
        ctrl.save_or_update_profile("Alpha", BASIC_CONFIG)
        assert len(fired) == 1

    def test_calls_layer_manager_when_present(
        self, ctrl_with_lm: ProfileController, mock_lm: MagicMock
    ) -> None:
        ctrl_with_lm.save_or_update_profile("Alpha", BASIC_CONFIG)
        mock_lm.create_all_layers.assert_called_once_with(BASIC_CONFIG)
        mock_lm.populate_layers_from_config.assert_called_once_with(BASIC_CONFIG)

    def test_returns_false_on_pm_error(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        mock_pm.save_profile.side_effect = RuntimeError("disk full")
        result = ctrl.save_or_update_profile("Alpha", BASIC_CONFIG)
        assert result is False

    def test_emits_error_message_on_pm_error(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        mock_pm.save_profile.side_effect = RuntimeError("disk full")
        received: list[tuple] = []
        ctrl.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl.save_or_update_profile("Alpha", BASIC_CONFIG)
        assert received[0][2] == _CRITICAL


# ---------------------------------------------------------------------------
# delete_profiles tests
# ---------------------------------------------------------------------------


class TestDeleteProfiles:
    def test_calls_delete_for_each_id(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        ctrl.delete_profiles(["id-1", "id-2"])
        assert mock_pm.delete_profile.call_count == 2

    def test_returns_deleted_count(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        count = ctrl.delete_profiles(["id-1", "id-2", "id-3"])
        assert count == 3

    def test_emits_profiles_changed_when_any_deleted(self, ctrl: ProfileController) -> None:
        fired: list[bool] = []
        ctrl.profiles_changed.connect(lambda: fired.append(True))
        ctrl.delete_profiles(["id-1"])
        assert len(fired) == 1

    def test_does_not_emit_profiles_changed_when_none_deleted(
        self, ctrl: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.delete_profile.side_effect = RuntimeError("not found")
        fired: list[bool] = []
        ctrl.profiles_changed.connect(lambda: fired.append(True))
        ctrl.delete_profiles(["bad-id"])
        assert len(fired) == 0

    def test_skips_failed_deletes_and_counts_successes(
        self, ctrl: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.delete_profile.side_effect = [None, RuntimeError("gone"), None]
        count = ctrl.delete_profiles(["id-1", "id-2", "id-3"])
        assert count == 2

    def test_empty_list_returns_zero(self, ctrl: ProfileController) -> None:
        assert ctrl.delete_profiles([]) == 0


# ---------------------------------------------------------------------------
# rename_profile tests
# ---------------------------------------------------------------------------


class TestRenameProfile:
    def test_calls_update_profile(self, ctrl: ProfileController, mock_pm: MagicMock) -> None:
        ctrl.rename_profile("id-1", "New Name")
        mock_pm.update_profile.assert_called_once_with("id-1", "New Name", BASIC_CONFIG)

    def test_returns_true_on_success(self, ctrl: ProfileController) -> None:
        assert ctrl.rename_profile("id-1", "New Name") is True

    def test_emits_profiles_changed_on_success(self, ctrl: ProfileController) -> None:
        fired: list[bool] = []
        ctrl.profiles_changed.connect(lambda: fired.append(True))
        ctrl.rename_profile("id-1", "New Name")
        assert len(fired) == 1

    def test_returns_false_when_profile_not_found(
        self, ctrl: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.get_profile.return_value = None
        assert ctrl.rename_profile("unknown", "New Name") is False

    def test_emits_error_when_profile_not_found(
        self, ctrl: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.get_profile.return_value = None
        received: list[tuple] = []
        ctrl.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl.rename_profile("unknown", "New Name")
        assert received[0][2] == _CRITICAL


# ---------------------------------------------------------------------------
# draw_profile tests
# ---------------------------------------------------------------------------


class TestDrawProfile:
    def test_calls_layer_manager(
        self, ctrl_with_lm: ProfileController, mock_lm: MagicMock
    ) -> None:
        ctrl_with_lm.draw_profile("id-1")
        mock_lm.create_all_layers.assert_called_once_with(BASIC_CONFIG)
        mock_lm.populate_layers_from_config.assert_called_once_with(BASIC_CONFIG)

    def test_returns_true_on_success(self, ctrl_with_lm: ProfileController) -> None:
        assert ctrl_with_lm.draw_profile("id-1") is True

    def test_emits_success_message(self, ctrl_with_lm: ProfileController) -> None:
        received: list[tuple] = []
        ctrl_with_lm.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl_with_lm.draw_profile("id-1")
        assert received[0][0] == "Profile Drawn"
        assert received[0][2] == _SUCCESS

    def test_returns_false_when_no_layer_manager(self, ctrl: ProfileController) -> None:
        assert ctrl.draw_profile("id-1") is False

    def test_returns_false_when_profile_not_found(
        self, ctrl_with_lm: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.get_profile.return_value = None
        assert ctrl_with_lm.draw_profile("missing") is False

    def test_emits_error_on_layer_failure(
        self, ctrl_with_lm: ProfileController, mock_lm: MagicMock
    ) -> None:
        mock_lm.create_all_layers.side_effect = RuntimeError("layer error")
        received: list[tuple] = []
        ctrl_with_lm.message.connect(lambda t, x, l: received.append((t, x, l)))
        result = ctrl_with_lm.draw_profile("id-1")
        assert result is False
        assert received[0][2] == _CRITICAL


# ---------------------------------------------------------------------------
# generate_vertical_scale tests (Issue #57)
# ---------------------------------------------------------------------------


class TestGenerateVerticalScale:
    def test_calls_layer_manager(
        self, ctrl_with_lm: ProfileController, mock_lm: MagicMock
    ) -> None:
        ctrl_with_lm.generate_vertical_scale("id-1")
        mock_lm.populate_vertical_scale_layer.assert_called_once_with(BASIC_CONFIG)

    def test_returns_true_on_success(self, ctrl_with_lm: ProfileController) -> None:
        assert ctrl_with_lm.generate_vertical_scale("id-1") is True

    def test_emits_success_message(self, ctrl_with_lm: ProfileController) -> None:
        received: list[tuple] = []
        ctrl_with_lm.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl_with_lm.generate_vertical_scale("id-1")
        assert received[0][0] == "Vertical Scale"
        assert received[0][2] == _SUCCESS

    def test_returns_false_when_no_layer_manager(self, ctrl: ProfileController) -> None:
        assert ctrl.generate_vertical_scale("id-1") is False

    def test_returns_false_when_profile_not_found(
        self, ctrl_with_lm: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.get_profile.return_value = None
        assert ctrl_with_lm.generate_vertical_scale("missing") is False

    def test_emits_error_when_profile_not_found(
        self, ctrl_with_lm: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.get_profile.return_value = None
        received: list[tuple] = []
        ctrl_with_lm.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl_with_lm.generate_vertical_scale("missing")
        assert received[0][2] == _CRITICAL

    def test_emits_error_on_value_error(
        self, ctrl_with_lm: ProfileController, mock_lm: MagicMock
    ) -> None:
        mock_lm.populate_vertical_scale_layer.side_effect = ValueError("bad geom")
        received: list[tuple] = []
        ctrl_with_lm.message.connect(lambda t, x, l: received.append((t, x, l)))
        result = ctrl_with_lm.generate_vertical_scale("id-1")
        assert result is False
        assert received[0][2] == _CRITICAL


# ---------------------------------------------------------------------------
# generate_distance_altitude_table tests (Issue #58)
# ---------------------------------------------------------------------------


class TestGenerateDistanceAltitudeTable:
    def test_calls_layout_manager(
        self,
        ctrl_with_layout: ProfileController,
        mock_layout_mgr: MagicMock,
    ) -> None:
        ctrl_with_layout.generate_distance_altitude_table("id-1")
        mock_layout_mgr.populate_distance_altitude_table.assert_called_once_with(BASIC_CONFIG)

    def test_returns_true_on_success(self, ctrl_with_layout: ProfileController) -> None:
        assert ctrl_with_layout.generate_distance_altitude_table("id-1") is True

    def test_emits_success_message(self, ctrl_with_layout: ProfileController) -> None:
        received: list[tuple] = []
        ctrl_with_layout.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl_with_layout.generate_distance_altitude_table("id-1")
        assert received[0][0] == "Distance/Altitude Table"
        assert received[0][2] == _SUCCESS

    def test_returns_false_when_no_layout_manager(self, ctrl: ProfileController) -> None:
        assert ctrl.generate_distance_altitude_table("id-1") is False

    def test_returns_false_when_profile_not_found(
        self, ctrl_with_layout: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.get_profile.return_value = None
        assert ctrl_with_layout.generate_distance_altitude_table("missing") is False

    def test_emits_error_when_profile_not_found(
        self, ctrl_with_layout: ProfileController, mock_pm: MagicMock
    ) -> None:
        mock_pm.get_profile.return_value = None
        received: list[tuple] = []
        ctrl_with_layout.message.connect(lambda t, x, l: received.append((t, x, l)))
        ctrl_with_layout.generate_distance_altitude_table("missing")
        assert received[0][2] == _CRITICAL

    def test_emits_error_on_attribute_error(
        self, ctrl_with_layout: ProfileController, mock_layout_mgr: MagicMock
    ) -> None:
        mock_layout_mgr.populate_distance_altitude_table.side_effect = AttributeError("layout gone")
        received: list[tuple] = []
        ctrl_with_layout.message.connect(lambda t, x, l: received.append((t, x, l)))
        result = ctrl_with_layout.generate_distance_altitude_table("id-1")
        assert result is False
        assert received[0][2] == _CRITICAL
