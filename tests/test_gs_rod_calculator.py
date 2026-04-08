"""Unit tests for gs_rod_calculator — Issue #73."""
import pytest
from qAeroChart.core.gs_rod_calculator import (
    GsRodConfig,
    compute_timing,
    compute_rod,
    compute_table,
    DEFAULT_GS_VALUES,
)


# ── Timing formula ─────────────────────────────────────────────────────────────

class TestTimingFormula:
    """Verify compute_timing against Image 1 expected values (5.2 NM)."""

    DISTANCE = 5.2

    @pytest.mark.parametrize("gs, expected", [
        (70,  "04:27"),
        (90,  "03:28"),
        (100, "03:07"),
        (120, "02:36"),
        (140, "02:14"),
        (160, "01:57"),
    ])
    def test_image1_values(self, gs, expected):
        assert compute_timing(self.DISTANCE, gs) == expected


class TestTimingFormulaImage2:
    """Verify compute_timing against Image 2 expected values (4.8 NM)."""

    DISTANCE = 4.8

    @pytest.mark.parametrize("gs, expected", [
        (90,  "03:12"),
        (100, "02:53"),
        (120, "02:24"),
        (140, "02:03"),
        (160, "01:48"),
    ])
    def test_image2_values(self, gs, expected):
        assert compute_timing(self.DISTANCE, gs) == expected


# ── ROD formula ────────────────────────────────────────────────────────────────

class TestRodFormula:
    """Verify compute_rod against Image 1 expected values (5.3 %)."""

    GRADIENT = 5.3

    @pytest.mark.parametrize("gs, expected", [
        (70,  375),
        (90,  482),
        (100, 536),
        (120, 643),
        (140, 750),
        (160, 857),
    ])
    def test_image1_values(self, gs, expected):
        assert compute_rod(gs, self.GRADIENT) == expected


class TestRodFormulaMonotonicity:
    """ROD increases with both GS and gradient."""

    def test_increases_with_gs(self):
        gradient = 5.3
        values = [compute_rod(gs, gradient) for gs in DEFAULT_GS_VALUES]
        assert values == sorted(values)

    def test_increases_with_gradient(self):
        gs = 100
        assert compute_rod(gs, 3.0) < compute_rod(gs, 5.0) < compute_rod(gs, 7.0)


# ── compute_table structure ────────────────────────────────────────────────────

class TestComputeTableWithTitle:
    """Table with title row, no footer."""

    @pytest.fixture
    def cfg(self):
        return GsRodConfig(distance_nm=5.2, gradient_pct=5.3, title="Rate of Descent", footer="")

    def test_row_count(self, cfg):
        rows = compute_table(cfg)
        # title + header + timing + rod = 4
        assert len(rows) == 4

    def test_title_in_first_col(self, cfg):
        rows = compute_table(cfg)
        assert rows[0][0] == "Rate of Descent"

    def test_title_row_rest_empty(self, cfg):
        rows = compute_table(cfg)
        assert all(v == "" for v in rows[0][1:])

    def test_header_row_structure(self, cfg):
        rows = compute_table(cfg)
        header = rows[1]
        assert header[0] == "Ground Speed"
        assert header[1] == "KT"
        assert header[2] == "70"

    def test_timing_row_label(self, cfg):
        rows = compute_table(cfg)
        assert "5.2" in rows[2][0]

    def test_rod_row_label(self, cfg):
        rows = compute_table(cfg)
        assert "5.3" in rows[3][0]

    def test_timing_values_correct(self, cfg):
        rows = compute_table(cfg)
        timing_row = rows[2]
        assert timing_row[2] == "04:27"  # 70 kt
        assert timing_row[7] == "01:57"  # 160 kt

    def test_rod_values_correct(self, cfg):
        rows = compute_table(cfg)
        rod_row = rows[3]
        assert rod_row[2] == "375"  # 70 kt
        assert rod_row[7] == "857"  # 160 kt


class TestComputeTableWithFooter:
    """Table with title row AND footer row."""

    @pytest.fixture
    def cfg(self):
        return GsRodConfig(
            distance_nm=4.8, gradient_pct=5.0,
            title="Rate of Descent",
            footer="Timing not authorized for defining the MAPt",
        )

    def test_row_count(self, cfg):
        rows = compute_table(cfg)
        # title + header + timing + rod + footer = 5
        assert len(rows) == 5

    def test_footer_in_last_row(self, cfg):
        rows = compute_table(cfg)
        assert "Timing not authorized" in rows[-1][0]

    def test_footer_rest_empty(self, cfg):
        rows = compute_table(cfg)
        assert all(v == "" for v in rows[-1][1:])


class TestComputeTableNoTitleNoFooter:
    """Minimal table: no title, no footer."""

    @pytest.fixture
    def cfg(self):
        return GsRodConfig(distance_nm=5.2, gradient_pct=5.3, title="", footer="")

    def test_row_count(self, cfg):
        rows = compute_table(cfg)
        # header + timing + rod = 3
        assert len(rows) == 3

    def test_first_row_is_header(self, cfg):
        rows = compute_table(cfg)
        assert rows[0][0] == "Ground Speed"

    def test_column_count(self, cfg):
        rows = compute_table(cfg)
        expected_cols = len(DEFAULT_GS_VALUES) + 2  # label + unit + gs columns
        for row in rows:
            assert len(row) == expected_cols


class TestCustomGsValues:
    """Table with different GS column list (Image 2 style)."""

    @pytest.fixture
    def cfg(self):
        return GsRodConfig(
            distance_nm=4.8, gradient_pct=5.0,
            gs_values=(90, 100, 120, 140, 160),
            title="",
            footer="",
        )

    def test_column_count(self, cfg):
        rows = compute_table(cfg)
        assert len(rows[0]) == 7  # label + unit + 5 GS values

    def test_first_gs_header(self, cfg):
        rows = compute_table(cfg)
        assert rows[0][2] == "90"


class TestCustomLabels:
    """Explicit label_timing and label_rod are used as-is."""

    def test_explicit_labels(self):
        cfg = GsRodConfig(
            distance_nm=5.2, gradient_pct=5.3,
            label_timing="FAF-MAPt 5.2NM",
            label_rod="Rate of Descent 5.3%",
            title="",
            footer="",
        )
        rows = compute_table(cfg)
        assert rows[1][0] == "FAF-MAPt 5.2NM"
        assert rows[2][0] == "Rate of Descent 5.3%"


class TestDefaultGsValues:
    def test_default_gs_values(self):
        assert DEFAULT_GS_VALUES == (70, 90, 100, 120, 140, 160)
