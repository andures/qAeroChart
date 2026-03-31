# tests/test_json_handler.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from qAeroChart.utils.json_handler import JSONHandler

# Full config matching _validate_config requirements (all runway keys required)
MINIMAL_CONFIG = {
    "origin_point": {"x": 100.0, "y": 200.0},
    "runway": {
        "direction": "09/27",
        "length": "3000",
        "thr_elevation": "500",
        "tch_rdh": "50",
    },
    "profile_points": [
        {"point_name": "MAPt", "distance_nm": "0.0", "elevation_ft": "500"}
    ],
}


class TestSaveLoad:
    def test_round_trip(self, tmp_path):
        path = str(tmp_path / "profile.json")
        assert JSONHandler.save_config(MINIMAL_CONFIG, path)
        loaded = JSONHandler.load_config(path)
        assert loaded is not None
        assert loaded["runway"]["direction"] == "09/27"

    def test_metadata_added_on_save(self, tmp_path):
        path = str(tmp_path / "p.json")
        JSONHandler.save_config(MINIMAL_CONFIG, path)
        with open(path) as f:
            raw = json.load(f)
        assert "metadata" in raw
        assert "version" in raw["metadata"]

    def test_save_invalid_config_raises(self, tmp_path):
        """save_config raises ValueError for configs missing required keys."""
        path = str(tmp_path / "bad.json")
        with pytest.raises(Exception):
            JSONHandler.save_config({}, path)

    def test_load_nonexistent_raises(self):
        """load_config raises FileNotFoundError for missing files."""
        with pytest.raises(Exception):
            JSONHandler.load_config("/nonexistent/path/file.json")

    def test_origin_point_stored_both_keys(self, tmp_path):
        """Saved file contains both origin_point and reference_point for compat."""
        path = str(tmp_path / "compat.json")
        JSONHandler.save_config(MINIMAL_CONFIG, path)
        with open(path) as f:
            raw = json.load(f)
        assert "origin_point" in raw
        assert "reference_point" in raw

    def test_profile_points_preserved(self, tmp_path):
        path = str(tmp_path / "pts.json")
        JSONHandler.save_config(MINIMAL_CONFIG, path)
        loaded = JSONHandler.load_config(path)
        assert len(loaded["profile_points"]) == 1
        assert loaded["profile_points"][0]["point_name"] == "MAPt"

    def test_backward_compat_reference_point_key(self, tmp_path):
        """v1 files that only have 'reference_point' (no 'origin_point') still load."""
        path = str(tmp_path / "v1.json")
        v1_data = {
            "metadata": {"version": "1.0"},
            "reference_point": {"x": 100.0, "y": 200.0},
            "runway": {
                "direction": "09/27",
                "length": "3000",
                "thr_elevation": "500",
                "tch_rdh": "50",
            },
            "profile_points": [{"point_name": "FAF"}],
        }
        with open(path, "w") as f:
            json.dump(v1_data, f)
        loaded = JSONHandler.load_config(path)
        assert loaded is not None
        assert loaded["reference_point"]["x"] == pytest.approx(100.0)


class TestDefaultFilename:
    def test_contains_direction(self):
        name = JSONHandler.get_default_filename("09/27")
        assert "09-27" in name

    def test_ends_with_json(self):
        name = JSONHandler.get_default_filename()
        assert name.endswith(".json")
