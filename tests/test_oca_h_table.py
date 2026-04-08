"""Tests for OCA/H table core (Issue #74)."""
from __future__ import annotations

import pytest

from qAeroChart.core.oca_h_table import (
    DEFAULT_CATEGORY_HEADERS,
    OcaHConfig,
    OcaHRow,
    compute_table,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def basic_rows() -> tuple[OcaHRow, ...]:
    return (
        OcaHRow("ILS CAT I", ("324 (161)", "334 (171)", "346 (183)", "361 (198)")),
        OcaHRow("LOC", ("600 (440)", "600 (440)", "600 (440)", "600 (440)")),
        OcaHRow("LOC WO SDF", ("800 (640)", "800 (640)", "800 (640)", "800 (640)")),
    )


@pytest.fixture
def basic_cfg(basic_rows) -> OcaHConfig:
    return OcaHConfig(rows=basic_rows)


# ------------------------------------------------------------------
# Default configuration
# ------------------------------------------------------------------

class TestDefaultConfig:
    def test_default_header_col0(self):
        cfg = OcaHConfig()
        assert cfg.header_col0 == "OCA (H)"

    def test_default_category_headers(self):
        cfg = OcaHConfig()
        assert cfg.category_headers == DEFAULT_CATEGORY_HEADERS

    def test_default_gs_values(self):
        assert DEFAULT_CATEGORY_HEADERS == ("A", "B", "C", "D")

    def test_default_no_title(self):
        cfg = OcaHConfig()
        assert cfg.title == ""

    def test_default_no_footer(self):
        cfg = OcaHConfig()
        assert cfg.footer == ""

    def test_frozen(self):
        cfg = OcaHConfig()
        with pytest.raises((TypeError, AttributeError)):
            cfg.header_col0 = "changed"  # type: ignore[misc]


# ------------------------------------------------------------------
# compute_table structure
# ------------------------------------------------------------------

class TestComputeTableStructure:
    def test_no_title_no_footer_row_count(self, basic_cfg, basic_rows):
        rows = compute_table(basic_cfg)
        # 1 header + 3 data rows
        assert len(rows) == 4

    def test_with_title_row_count(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, title="Approach Minimums")
        rows = compute_table(cfg)
        # title + header + 3 data
        assert len(rows) == 5

    def test_with_footer_row_count(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, footer="Values in feet")
        rows = compute_table(cfg)
        # header + 3 data + footer
        assert len(rows) == 5

    def test_with_title_and_footer_row_count(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, title="T", footer="F")
        rows = compute_table(cfg)
        # title + header + 3 data + footer
        assert len(rows) == 6

    def test_column_count(self, basic_cfg):
        rows = compute_table(basic_cfg)
        # 1 procedure col + 4 category cols
        for row in rows:
            assert len(row) == 5

    def test_empty_rows(self):
        cfg = OcaHConfig()
        rows = compute_table(cfg)
        # only header
        assert len(rows) == 1
        assert rows[0][0] == "OCA (H)"


# ------------------------------------------------------------------
# Header row content
# ------------------------------------------------------------------

class TestHeaderRow:
    def test_header_col0_default(self, basic_cfg):
        rows = compute_table(basic_cfg)
        assert rows[0][0] == "OCA (H)"

    def test_header_col0_custom(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, header_col0="Min Alt")
        rows = compute_table(cfg)
        assert rows[0][0] == "Min Alt"

    def test_header_categories_default(self, basic_cfg):
        rows = compute_table(basic_cfg)
        assert rows[0][1:] == ["A", "B", "C", "D"]

    def test_header_categories_custom(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, category_headers=("I", "II", "III"))
        rows = compute_table(cfg)
        assert rows[0][1:] == ["I", "II", "III"]


# ------------------------------------------------------------------
# Data row content
# ------------------------------------------------------------------

class TestDataRows:
    def test_first_data_row_procedure(self, basic_cfg):
        rows = compute_table(basic_cfg)
        assert rows[1][0] == "ILS CAT I"

    def test_first_data_row_values(self, basic_cfg):
        rows = compute_table(basic_cfg)
        assert rows[1][1] == "324 (161)"
        assert rows[1][2] == "334 (171)"
        assert rows[1][3] == "346 (183)"
        assert rows[1][4] == "361 (198)"

    def test_loc_row(self, basic_cfg):
        rows = compute_table(basic_cfg)
        assert rows[2][0] == "LOC"
        assert rows[2][1] == "600 (440)"

    def test_loc_wo_sdf_row(self, basic_cfg):
        rows = compute_table(basic_cfg)
        assert rows[3][0] == "LOC WO SDF"
        assert rows[3][1] == "800 (640)"


# ------------------------------------------------------------------
# Title and footer rows
# ------------------------------------------------------------------

class TestTitleFooterRows:
    def test_title_in_col0(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, title="Approach Minimums")
        rows = compute_table(cfg)
        assert rows[0][0] == "Approach Minimums"

    def test_title_rest_empty(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, title="Approach Minimums")
        rows = compute_table(cfg)
        assert all(c == "" for c in rows[0][1:])

    def test_footer_in_col0(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, footer="Values in feet")
        rows = compute_table(cfg)
        assert rows[-1][0] == "Values in feet"

    def test_footer_rest_empty(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, footer="Values in feet")
        rows = compute_table(cfg)
        assert all(c == "" for c in rows[-1][1:])

    def test_title_row_is_first(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, title="T")
        rows = compute_table(cfg)
        assert rows[0][0] == "T"
        assert rows[1][0] == "OCA (H)"

    def test_footer_row_is_last(self, basic_rows):
        cfg = OcaHConfig(rows=basic_rows, footer="F")
        rows = compute_table(cfg)
        assert rows[-1][0] == "F"


# ------------------------------------------------------------------
# Value padding / truncation
# ------------------------------------------------------------------

class TestValuePadding:
    def test_short_values_padded_with_empty(self):
        cfg = OcaHConfig(
            rows=(OcaHRow("ILS", ("300",)),),
            category_headers=("A", "B", "C"),
        )
        rows = compute_table(cfg)
        data_row = rows[1]
        assert data_row[1] == "300"
        assert data_row[2] == ""
        assert data_row[3] == ""

    def test_extra_values_truncated(self):
        cfg = OcaHConfig(
            rows=(OcaHRow("ILS", ("1", "2", "3", "4", "5")),),
            category_headers=("A", "B"),
        )
        rows = compute_table(cfg)
        data_row = rows[1]
        assert len(data_row) == 3  # procedure + A + B
        assert data_row[1] == "1"
        assert data_row[2] == "2"


# ------------------------------------------------------------------
# OcaHRow
# ------------------------------------------------------------------

class TestOcaHRow:
    def test_frozen(self):
        row = OcaHRow("ILS", ("300",))
        with pytest.raises((TypeError, AttributeError)):
            row.procedure = "changed"  # type: ignore[misc]

    def test_procedure_and_values(self):
        row = OcaHRow("LOC", ("500", "510"))
        assert row.procedure == "LOC"
        assert row.values == ("500", "510")
