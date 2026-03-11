# tests/test_distance_altitude_table.py
"""
Unit tests for the distance/altitude table helpers (Issue #58).
All tested functions are pure Python — no QGIS mocks needed.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from qAeroChart.core.distance_altitude_table import (
    build_table_rows,
    compute_column_widths,
    extract_table_data,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NUMERIC_COLS: dict[str, str] = {
    "3.0": "4200",
    "6.0": "5100",
    "9.0": "6300",
    "12.0": "7500",
}

BASIC_CONFIG: dict = {
    "runway": {"direction": "07", "thr_elevation": "13"},
    "profile_points": [
        {"point_name": "THR", "distance_nm": "0.0", "elevation_ft": "200"},
        {"point_name": "MAPt", "distance_nm": "3.0", "elevation_ft": "4200"},
        {"point_name": "FAF", "distance_nm": "6.0", "elevation_ft": "5100"},
    ],
}


# ---------------------------------------------------------------------------
# TestBuildTableRows
# ---------------------------------------------------------------------------


class TestBuildTableRows:
    def test_header_first_cell(self) -> None:
        headers, _ = build_table_rows("07", NUMERIC_COLS)
        assert headers[0] == "NM TO RWY07"

    def test_header_length(self) -> None:
        headers, _ = build_table_rows("07", NUMERIC_COLS)
        assert len(headers) == 1 + len(NUMERIC_COLS)

    def test_value_first_cell(self) -> None:
        _, values = build_table_rows("07", NUMERIC_COLS)
        assert values[0] == "ALTITUDE"

    def test_value_length(self) -> None:
        _, values = build_table_rows("07", NUMERIC_COLS)
        assert len(values) == 1 + len(NUMERIC_COLS)

    def test_header_keys_in_order(self) -> None:
        headers, _ = build_table_rows("07", NUMERIC_COLS)
        assert headers[1:] == list(NUMERIC_COLS.keys())

    def test_values_in_order(self) -> None:
        _, values = build_table_rows("07", NUMERIC_COLS)
        assert values[1:] == list(NUMERIC_COLS.values())

    def test_empty_numeric_columns(self) -> None:
        headers, values = build_table_rows("27", {})
        assert headers == ["NM TO RWY27"]
        assert values == ["ALTITUDE"]

    def test_thr_formatting(self) -> None:
        headers, _ = build_table_rows("09", {"1.0": "3000"})
        assert headers[0] == "NM TO RWY09"


# ---------------------------------------------------------------------------
# TestComputeColumnWidths
# ---------------------------------------------------------------------------


class TestComputeColumnWidths:
    def test_single_column_returns_total_width(self) -> None:
        widths = compute_column_widths(1)
        assert widths == [180.20]

    def test_first_col_fixed(self) -> None:
        widths = compute_column_widths(5)
        assert widths[0] == pytest.approx(36.20)

    def test_total_count(self) -> None:
        widths = compute_column_widths(5)
        assert len(widths) == 5

    def test_dynamic_cols_are_equal(self) -> None:
        widths = compute_column_widths(5)
        dynamic = widths[1:]
        assert all(w == pytest.approx(dynamic[0]) for w in dynamic)

    def test_two_columns(self) -> None:
        widths = compute_column_widths(2)
        assert len(widths) == 2
        assert widths[0] == pytest.approx(36.20)

    def test_custom_total_width(self) -> None:
        widths = compute_column_widths(3, total_width=120.0, first_col_width=30.0)
        assert widths[0] == pytest.approx(30.0)
        assert len(widths) == 3

    def test_dynamic_width_is_positive(self) -> None:
        widths = compute_column_widths(10)
        assert all(w > 0 for w in widths)

    def test_matches_original_script_4_dynamic_cols(self) -> None:
        # Reproduce original script: 5 columns total (1 fixed + 4 dynamic)
        num_columns = 5
        stroke_width = 0.25
        cell_margin = 1.0
        total_width = 180.20
        first_col_width = 36.20
        num_dynamic = 4
        extra = (num_columns - 1) * stroke_width + 2 * cell_margin * num_columns
        expected_dynamic = (total_width - first_col_width - extra) / num_dynamic

        widths = compute_column_widths(5)
        assert widths[1] == pytest.approx(expected_dynamic)


# ---------------------------------------------------------------------------
# TestExtractTableData
# ---------------------------------------------------------------------------


class TestExtractTableData:
    def test_thr_extracted_from_direction(self) -> None:
        thr, _ = extract_table_data(BASIC_CONFIG)
        assert thr == "07"

    def test_numeric_columns_from_profile_points(self) -> None:
        _, cols = extract_table_data(BASIC_CONFIG)
        assert cols == {"0.0": "200", "3.0": "4200", "6.0": "5100"}

    def test_empty_profile_points(self) -> None:
        config = {"runway": {"direction": "18"}, "profile_points": []}
        thr, cols = extract_table_data(config)
        assert thr == "18"
        assert cols == {}

    def test_direction_letters_stripped(self) -> None:
        config = {"runway": {"direction": "09R"}, "profile_points": []}
        thr, _ = extract_table_data(config)
        assert thr == "09"

    def test_elevation_ft_used(self) -> None:
        config = {
            "runway": {"direction": "09"},
            "profile_points": [{"distance_nm": "1.0", "elevation_ft": "3000"}],
        }
        _, cols = extract_table_data(config)
        assert cols["1.0"] == "3000"

    def test_elevation_fallback_when_no_elevation_ft(self) -> None:
        config = {
            "runway": {"direction": "09"},
            "profile_points": [{"distance_nm": "1.0", "elevation": "3000"}],
        }
        _, cols = extract_table_data(config)
        assert cols["1.0"] == "3000"

    def test_skips_point_missing_distance(self) -> None:
        config = {
            "runway": {"direction": "09"},
            "profile_points": [{"point_name": "XXX", "elevation_ft": "500"}],
        }
        _, cols = extract_table_data(config)
        assert cols == {}

    def test_skips_point_missing_elevation(self) -> None:
        config = {
            "runway": {"direction": "09"},
            "profile_points": [{"distance_nm": "1.0"}],
        }
        _, cols = extract_table_data(config)
        assert cols == {}

    def test_missing_runway_defaults(self) -> None:
        config = {"profile_points": []}
        thr, cols = extract_table_data(config)
        assert thr == "00"
        assert cols == {}
