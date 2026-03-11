# tests/test_vertical_scale_manager.py
"""
Unit tests for VerticalScaleManager.

QgsProject is replaced by a lightweight in-memory store so these tests
run without a running QGIS instance.
"""
from __future__ import annotations

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

import tests.mocks.qgis_mock  # noqa: F401

from qAeroChart.core.vertical_scale_manager import VerticalScaleManager


# ---------------------------------------------------------------------------
# Fake QgsProject that stores data in a plain dict
# ---------------------------------------------------------------------------

class _FakeProject:
    """Minimal QgsProject substitute for unit tests."""

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
def mgr(fake_project: _FakeProject) -> VerticalScaleManager:
    """VerticalScaleManager with QgsProject patched to the fake store."""
    with patch(
        "qAeroChart.core.vertical_scale_manager.QgsProject",
        **{"instance.return_value": fake_project},
    ):
        yield VerticalScaleManager()


# ---------------------------------------------------------------------------
# save_new / get_config
# ---------------------------------------------------------------------------

class TestSaveAndGet:
    def test_save_returns_id_with_prefix(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "Test Scale"})
        assert sid.startswith("vscale_")

    def test_save_two_returns_different_ids(self, mgr: VerticalScaleManager) -> None:
        id1 = mgr.save_new({"name": "A"})
        id2 = mgr.save_new({"name": "B"})
        assert id1 != id2

    def test_get_config_returns_saved_params(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "My Scale", "angle": 90.0})
        cfg = mgr.get_config(sid)
        assert cfg is not None
        assert cfg["name"] == "My Scale"
        assert cfg["angle"] == pytest.approx(90.0)

    def test_get_config_returns_none_for_unknown_id(self, mgr: VerticalScaleManager) -> None:
        assert mgr.get_config("does_not_exist") is None


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------

class TestGetAll:
    def test_empty_on_fresh_manager(self, mgr: VerticalScaleManager) -> None:
        assert mgr.get_all() == []

    def test_returns_metadata_after_save(self, mgr: VerticalScaleManager) -> None:
        mgr.save_new({"name": "Alpha"})
        items = mgr.get_all()
        assert len(items) == 1
        assert items[0]["name"] == "Alpha"
        assert "id" in items[0]
        assert "created" in items[0]

    def test_returns_multiple_in_order(self, mgr: VerticalScaleManager) -> None:
        mgr.save_new({"name": "A"})
        mgr.save_new({"name": "B"})
        names = [it["name"] for it in mgr.get_all()]
        assert names == ["A", "B"]


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------

class TestRename:
    def test_rename_updates_name_in_list(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "Old"})
        result = mgr.rename(sid, "New")
        assert result is True
        names = [it["name"] for it in mgr.get_all()]
        assert "New" in names
        assert "Old" not in names

    def test_rename_unknown_id_returns_false(self, mgr: VerticalScaleManager) -> None:
        assert mgr.rename("nonexistent", "Whatever") is False

    def test_rename_does_not_change_config(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "Old", "angle": 45.0})
        mgr.rename(sid, "New")
        cfg = mgr.get_config(sid)
        assert cfg is not None
        assert cfg["angle"] == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_removes_from_list(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "Temp"})
        assert mgr.delete(sid) is True
        assert not any(it["id"] == sid for it in mgr.get_all())

    def test_delete_removes_config(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "Temp"})
        mgr.delete(sid)
        assert mgr.get_config(sid) is None

    def test_delete_unknown_id_returns_false(self, mgr: VerticalScaleManager) -> None:
        assert mgr.delete("nonexistent") is False

    def test_delete_does_not_affect_other_entries(self, mgr: VerticalScaleManager) -> None:
        s1 = mgr.save_new({"name": "Keep"})
        s2 = mgr.save_new({"name": "Remove"})
        mgr.delete(s2)
        remaining_ids = [it["id"] for it in mgr.get_all()]
        assert s1 in remaining_ids
        assert s2 not in remaining_ids


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_overwrites_config(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "V1", "angle": 0.0})
        mgr.update(sid, {"name": "V2", "angle": 180.0})
        cfg = mgr.get_config(sid)
        assert cfg is not None
        assert cfg["angle"] == pytest.approx(180.0)

    def test_update_reflects_new_name_in_list(self, mgr: VerticalScaleManager) -> None:
        sid = mgr.save_new({"name": "V1"})
        mgr.update(sid, {"name": "V2"})
        names = [it["name"] for it in mgr.get_all()]
        assert "V2" in names


# ---------------------------------------------------------------------------
# load_all_configs
# ---------------------------------------------------------------------------

class TestLoadAllConfigs:
    def test_returns_all_full_configs(self, mgr: VerticalScaleManager) -> None:
        mgr.save_new({"name": "A", "angle": 10.0})
        mgr.save_new({"name": "B", "angle": 20.0})
        configs = mgr.load_all_configs()
        assert len(configs) == 2
        angles = {c["angle"] for c in configs}
        assert angles == {10.0, 20.0}

    def test_empty_when_no_scales(self, mgr: VerticalScaleManager) -> None:
        assert mgr.load_all_configs() == []
