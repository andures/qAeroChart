# tests/test_table_style_manager.py
"""
Unit tests for TableStyleManager (Issue #71).

QgsProject is replaced by a lightweight in-memory store so these tests
run without a running QGIS instance.  Same pattern as test_vertical_scale_manager.py.
"""
from __future__ import annotations

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

import tests.mocks.qgis_mock  # noqa: F401

from qAeroChart.core.table_style_manager import TableStyleManager, BUILTIN_STYLES


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
def mgr(fake_project: _FakeProject) -> TableStyleManager:
    """TableStyleManager with QgsProject patched to the fake store."""
    with patch(
        "qAeroChart.core.table_style_manager.QgsProject",
        **{"instance.return_value": fake_project},
    ):
        yield TableStyleManager()


# ---------------------------------------------------------------------------
# Built-in styles
# ---------------------------------------------------------------------------

class TestBuiltinStyles:
    def test_builtin_names_present(self) -> None:
        assert "Default" in BUILTIN_STYLES
        assert "ICAO" in BUILTIN_STYLES

    def test_default_has_required_keys(self) -> None:
        cfg = BUILTIN_STYLES["Default"]
        for key in ("name", "top_left_text", "first_col_text", "total_width",
                    "first_col_width", "height", "stroke", "cell_margin",
                    "font_family", "font_size"):
            assert key in cfg, f"Missing key: {key}"

    def test_icao_top_left_text(self) -> None:
        assert "THR" in BUILTIN_STYLES["ICAO"]["top_left_text"]

    def test_default_top_left_text(self) -> None:
        assert "RWY" in BUILTIN_STYLES["Default"]["top_left_text"]

    def test_first_col_text_altitude(self) -> None:
        for style in BUILTIN_STYLES.values():
            assert style["first_col_text"] == "ALTITUDE"


# ---------------------------------------------------------------------------
# get_all — includes built-ins + project styles
# ---------------------------------------------------------------------------

class TestGetAll:
    def test_builtins_appear_first(self, mgr: TableStyleManager) -> None:
        all_styles = mgr.get_all()
        builtin_names = [s["name"] for s in all_styles if s["builtin"]]
        assert "Default" in builtin_names
        assert "ICAO" in builtin_names

    def test_builtins_flagged(self, mgr: TableStyleManager) -> None:
        for item in mgr.get_all():
            if item["name"] in BUILTIN_STYLES:
                assert item["builtin"] is True

    def test_project_style_flagged_not_builtin(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Custom"})
        project_items = [s for s in mgr.get_all() if not s["builtin"]]
        assert any(s["name"] == "Custom" for s in project_items)

    def test_empty_project_returns_only_builtins(self, mgr: TableStyleManager) -> None:
        all_styles = mgr.get_all()
        assert len(all_styles) == len(BUILTIN_STYLES)


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------

class TestGetConfig:
    def test_get_builtin_default(self, mgr: TableStyleManager) -> None:
        cfg = mgr.get_config("Default")
        assert cfg is not None
        assert cfg["name"] == "Default"

    def test_get_builtin_icao(self, mgr: TableStyleManager) -> None:
        cfg = mgr.get_config("ICAO")
        assert cfg is not None
        assert cfg["name"] == "ICAO"

    def test_get_nonexistent_returns_none(self, mgr: TableStyleManager) -> None:
        assert mgr.get_config("DoesNotExist") is None

    def test_get_project_style_after_save(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Honduras", "font_family": "Helvetica", "font_size": 9.0})
        cfg = mgr.get_config("Honduras")
        assert cfg is not None
        assert cfg["font_family"] == "Helvetica"

    def test_builtin_config_is_copy(self, mgr: TableStyleManager) -> None:
        """Ensure get_config returns a copy; mutating it does not affect BUILTIN_STYLES."""
        cfg = mgr.get_config("Default")
        cfg["name"] = "MUTATED"
        assert BUILTIN_STYLES["Default"]["name"] == "Default"


# ---------------------------------------------------------------------------
# save_new
# ---------------------------------------------------------------------------

class TestSaveNew:
    def test_returns_id_with_prefix(self, mgr: TableStyleManager) -> None:
        sid = mgr.save_new({"name": "A"})
        assert sid.startswith("tstyle_")

    def test_two_saves_produce_different_ids(self, mgr: TableStyleManager) -> None:
        id1 = mgr.save_new({"name": "A"})
        id2 = mgr.save_new({"name": "B"})
        assert id1 != id2

    def test_saved_style_appears_in_get_all(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Peru"})
        names = [s["name"] for s in mgr.get_all()]
        assert "Peru" in names

    def test_saved_style_config_retrievable(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Peru", "total_width": 200.0})
        cfg = mgr.get_config("Peru")
        assert cfg["total_width"] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_project_style(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Bolivia", "font_size": 8.0})
        result = mgr.update("Bolivia", {"name": "Bolivia", "font_size": 10.0})
        assert result is True
        cfg = mgr.get_config("Bolivia")
        assert cfg["font_size"] == pytest.approx(10.0)

    def test_update_builtin_returns_false(self, mgr: TableStyleManager) -> None:
        result = mgr.update("Default", {"name": "Default", "font_size": 99.0})
        assert result is False

    def test_update_nonexistent_returns_false(self, mgr: TableStyleManager) -> None:
        assert mgr.update("Ghost", {}) is False


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------

class TestRename:
    def test_rename_project_style(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Old"})
        result = mgr.rename("Old", "New")
        assert result is True
        names = [s["name"] for s in mgr.get_all()]
        assert "New" in names
        assert "Old" not in names

    def test_rename_builtin_returns_false(self, mgr: TableStyleManager) -> None:
        assert mgr.rename("Default", "NotDefault") is False
        # Built-in must be unchanged
        assert mgr.get_config("Default") is not None

    def test_rename_nonexistent_returns_false(self, mgr: TableStyleManager) -> None:
        assert mgr.rename("Ghost", "Spirit") is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_project_style(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Temp"})
        result = mgr.delete("Temp")
        assert result is True
        assert mgr.get_config("Temp") is None

    def test_delete_removes_from_get_all(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Temp2"})
        mgr.delete("Temp2")
        names = [s["name"] for s in mgr.get_all()]
        assert "Temp2" not in names

    def test_delete_builtin_returns_false(self, mgr: TableStyleManager) -> None:
        assert mgr.delete("Default") is False
        assert mgr.delete("ICAO") is False

    def test_delete_nonexistent_returns_false(self, mgr: TableStyleManager) -> None:
        assert mgr.delete("Ghost") is False


# ---------------------------------------------------------------------------
# load_all_configs
# ---------------------------------------------------------------------------

class TestLoadAllConfigs:
    def test_includes_builtins(self, mgr: TableStyleManager) -> None:
        all_cfgs = mgr.load_all_configs()
        names = [c["name"] for c in all_cfgs]
        assert "Default" in names
        assert "ICAO" in names

    def test_includes_project_styles(self, mgr: TableStyleManager) -> None:
        mgr.save_new({"name": "Ecuador"})
        all_cfgs = mgr.load_all_configs()
        names = [c["name"] for c in all_cfgs]
        assert "Ecuador" in names
