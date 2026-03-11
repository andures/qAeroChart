# tests/test_profile_manager.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from unittest.mock import MagicMock

# Import QGIS mocks first (sets sys.modules["qgis.core"] to our MagicMock stub)
import tests.mocks.qgis_mock  # noqa: F401

# In-memory project variable store
_store: dict = {}


def _write(ns, key, value):
    _store[f"{ns}/{key}"] = value


def _read(ns, key, default=""):
    return (_store.get(f"{ns}/{key}", default), True)


def _remove(ns, key):
    _store.pop(f"{ns}/{key}", None)


# Build the mock project and wire it to qgis.core.QgsProject BEFORE import
mock_project = MagicMock()
mock_project.readEntry.side_effect = _read
mock_project.writeEntry.side_effect = _write
mock_project.removeEntry.side_effect = _remove

sys.modules["qgis.core"].QgsProject.instance.return_value = mock_project

# Now importing ProfileManager will bind QgsProject.instance() → mock_project
from qAeroChart.core.profile_manager import ProfileManager  # noqa: E402


@pytest.fixture(autouse=True)
def clear_store():
    """Reset the fake project store between tests."""
    _store.clear()
    yield
    _store.clear()


@pytest.fixture()
def mgr():
    return ProfileManager()


BASIC_CONFIG = {
    "runway": {"direction": "09/27"},
    "profile_points": [{"point_name": "MAPt"}],
}


class TestGetAllProfiles:
    def test_empty_on_fresh_store(self, mgr):
        assert mgr.get_all_profiles() == []

    def test_returns_list(self, mgr):
        result = mgr.get_all_profiles()
        assert isinstance(result, list)


class TestSaveProfile:
    def test_returns_profile_id(self, mgr):
        pid = mgr.save_profile("Test", BASIC_CONFIG)
        assert isinstance(pid, str)
        assert pid.startswith("profile_")

    def test_profile_appears_in_list(self, mgr):
        mgr.save_profile("RWY 09", BASIC_CONFIG)
        profiles = mgr.get_all_profiles()
        assert len(profiles) == 1
        assert profiles[0]["name"] == "RWY 09"

    def test_two_saves_give_unique_ids(self, mgr):
        id1 = mgr.save_profile("P1", BASIC_CONFIG)
        id2 = mgr.save_profile("P2", BASIC_CONFIG)
        assert id1 != id2

    def test_multiple_saves_accumulate(self, mgr):
        mgr.save_profile("A", BASIC_CONFIG)
        mgr.save_profile("B", BASIC_CONFIG)
        assert len(mgr.get_all_profiles()) == 2


class TestGetProfile:
    def test_retrieve_saved_config(self, mgr):
        config = {"runway": {"direction": "07/25"}, "profile_points": []}
        pid = mgr.save_profile("RWY 07", config)
        loaded = mgr.get_profile(pid)
        assert loaded is not None
        assert loaded["runway"]["direction"] == "07/25"

    def test_nonexistent_returns_none(self, mgr):
        assert mgr.get_profile("nonexistent_id") is None


class TestUpdateProfile:
    def test_name_updated(self, mgr):
        pid = mgr.save_profile("Original", BASIC_CONFIG)
        updated = {**BASIC_CONFIG, "runway": {"direction": "27/09"}}
        mgr.update_profile(pid, "Updated", updated)
        profiles = mgr.get_all_profiles()
        assert profiles[0]["name"] == "Updated"

    def test_config_updated(self, mgr):
        config = {"runway": {"direction": "09/27"}, "profile_points": []}
        pid = mgr.save_profile("P", config)
        config["runway"]["direction"] = "27/09"
        mgr.update_profile(pid, "P-mod", config)
        loaded = mgr.get_profile(pid)
        assert loaded["runway"]["direction"] == "27/09"


class TestDeleteProfile:
    def test_delete_removes_from_list(self, mgr):
        pid = mgr.save_profile("ToDelete", BASIC_CONFIG)
        assert len(mgr.get_all_profiles()) == 1
        mgr.delete_profile(pid)
        assert mgr.get_all_profiles() == []

    def test_delete_config_no_longer_retrievable(self, mgr):
        pid = mgr.save_profile("Gone", BASIC_CONFIG)
        mgr.delete_profile(pid)
        assert mgr.get_profile(pid) is None

    def test_delete_one_of_two_keeps_other(self, mgr):
        pid1 = mgr.save_profile("Keep", BASIC_CONFIG)
        pid2 = mgr.save_profile("Delete", BASIC_CONFIG)
        mgr.delete_profile(pid2)
        profiles = mgr.get_all_profiles()
        assert len(profiles) == 1
        assert profiles[0]["id"] == pid1
