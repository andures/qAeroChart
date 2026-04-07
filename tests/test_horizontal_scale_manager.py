# tests/test_horizontal_scale_manager.py
"""Unit tests for HorizontalScaleManager — mirrors test_vertical_scale_manager.py."""
from __future__ import annotations

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

import tests.mocks.qgis_mock  # noqa: F401

from qAeroChart.core.horizontal_scale_manager import HorizontalScaleManager


# ---------------------------------------------------------------------------
# Fake QgsProject (same pattern as vertical scale manager tests)
# ---------------------------------------------------------------------------

class _FakeProject:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def writeEntry(self, section: str, key: str, value: str) -> None:
        self._store[f"{section}/{key}"] = value

    def readEntry(self, section: str, key: str, default: str = "") -> tuple[str, bool]:
        full_key = f"{section}/{key}"
        found = full_key in self._store
        return self._store.get(full_key, default), found

    def removeEntry(self, section: str, key: str) -> None:
        self._store.pop(f"{section}/{key}", None)


@pytest.fixture()
def fake_project() -> _FakeProject:
    return _FakeProject()


@pytest.fixture()
def mgr(fake_project: _FakeProject) -> HorizontalScaleManager:
    with patch(
        "qAeroChart.core.horizontal_scale_manager.QgsProject",
        **{"instance.return_value": fake_project},
    ):
        yield HorizontalScaleManager()


# ---------------------------------------------------------------------------
# save_new / get_config
# ---------------------------------------------------------------------------

class TestSaveAndGet:
    def test_save_returns_id_with_prefix(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "Test HScale"})
        assert sid.startswith("hscale_")

    def test_save_two_returns_different_ids(self, mgr: HorizontalScaleManager) -> None:
        id1 = mgr.save_new({"name": "A"})
        id2 = mgr.save_new({"name": "B"})
        assert id1 != id2

    def test_get_config_returns_saved_params(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "My HScale", "angle": 90.0})
        cfg = mgr.get_config(sid)
        assert cfg is not None
        assert cfg["name"] == "My HScale"
        assert cfg["angle"] == pytest.approx(90.0)

    def test_get_config_unknown_id_returns_none(self, mgr: HorizontalScaleManager) -> None:
        assert mgr.get_config("bogus_id") is None


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------

class TestGetAll:
    def test_empty_initially(self, mgr: HorizontalScaleManager) -> None:
        assert mgr.get_all() == []

    def test_contains_saved_entry(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "Scale A"})
        items = mgr.get_all()
        assert any(it["id"] == sid for it in items)

    def test_contains_name(self, mgr: HorizontalScaleManager) -> None:
        mgr.save_new({"name": "Scale B"})
        names = [it["name"] for it in mgr.get_all()]
        assert "Scale B" in names


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------

class TestRename:
    def test_rename_updates_name_in_list(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "Old Name"})
        mgr.rename(sid, "New Name")
        names = [it["name"] for it in mgr.get_all()]
        assert "New Name" in names
        assert "Old Name" not in names

    def test_rename_unknown_id_returns_false(self, mgr: HorizontalScaleManager) -> None:
        assert mgr.rename("ghost", "X") is False

    def test_rename_known_id_returns_true(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "A"})
        assert mgr.rename(sid, "B") is True


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_removes_from_list(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "To Delete"})
        mgr.delete(sid)
        ids = [it["id"] for it in mgr.get_all()]
        assert sid not in ids

    def test_delete_removes_config(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "Gone"})
        mgr.delete(sid)
        assert mgr.get_config(sid) is None

    def test_delete_unknown_id_returns_false(self, mgr: HorizontalScaleManager) -> None:
        assert mgr.delete("ghost") is False

    def test_delete_known_id_returns_true(self, mgr: HorizontalScaleManager) -> None:
        sid = mgr.save_new({"name": "A"})
        assert mgr.delete(sid) is True

    def test_delete_does_not_affect_other_entries(self, mgr: HorizontalScaleManager) -> None:
        sid1 = mgr.save_new({"name": "Keep"})
        sid2 = mgr.save_new({"name": "Remove"})
        mgr.delete(sid2)
        ids = [it["id"] for it in mgr.get_all()]
        assert sid1 in ids


# ---------------------------------------------------------------------------
# load_all_configs
# ---------------------------------------------------------------------------

class TestLoadAllConfigs:
    def test_returns_list_of_full_configs(self, mgr: HorizontalScaleManager) -> None:
        mgr.save_new({"name": "A", "angle": 45.0})
        mgr.save_new({"name": "B", "angle": 90.0})
        configs = mgr.load_all_configs()
        assert len(configs) == 2
        names = {c["name"] for c in configs}
        assert names == {"A", "B"}
