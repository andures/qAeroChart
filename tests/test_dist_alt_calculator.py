"""Unit tests for dist_alt_calculator — Issue #99."""
import pytest

from qAeroChart.core.dist_alt_calculator import (
    DistAltConfig,
    compute_steps,
    compute_summary,
    compute_table,
    steps_to_numeric_columns,
)

# Reference example from pansops-calculator docs/plan-136-dist-alt-calculator.md:
# FAF 6000 ft, THR/MAPt 1922 ft, distance 12.2 NM, TCH 49 ft, OCA 2450 ft.
REFERENCE_CFG = DistAltConfig(
    faf_altitude_ft=6000,
    thr_elevation_ft=1922,
    faf_thr_distance_nm=12.2,
    tch_rdh_ft=49,
    oca_ft=2450,
)


class TestSummary:
    def test_reference_example(self):
        summary = compute_summary(REFERENCE_CFG)
        assert summary["gradient_pct"] == pytest.approx(5.44, abs=0.01)
        assert summary["vpa_deg"] == pytest.approx(3.11, abs=0.01)
        assert summary["height_loss_per_mile_ft"] == 330


class TestSteps:
    def test_row_d12(self):
        steps = compute_steps(REFERENCE_CFG)
        row = next(s for s in steps if s.distance_label == "12")
        assert row.calculated_altitude_ft == pytest.approx(5933.95, abs=0.01)
        assert row.publication_altitude_ft == 5940
        assert row.calculated_height_ft == 4018

    def test_row_d0_equals_threshold_plus_tch(self):
        steps = compute_steps(REFERENCE_CFG)
        row = next(s for s in steps if s.distance_label == "0")
        assert row.calculated_altitude_ft == pytest.approx(
            REFERENCE_CFG.thr_elevation_ft + REFERENCE_CFG.tch_rdh_ft, abs=0.01
        )

    def test_row_count_matches_floor_distance_plus_one(self):
        steps = compute_steps(REFERENCE_CFG)
        assert len(steps) == 13  # floor(12.2) + 1 == 12 + 1

    def test_below_oca_advisory(self):
        cfg = DistAltConfig(
            faf_altitude_ft=3000,
            thr_elevation_ft=1922,
            faf_thr_distance_nm=10,
            tch_rdh_ft=49,
            oca_ft=2900,
        )
        steps = compute_steps(cfg)
        assert any(s.advisory_altitude == "below OCA" for s in steps)
        assert any(s.advisory_altitude != "below OCA" for s in steps)

    def test_offset_filters_non_positive_display_distance(self):
        cfg = DistAltConfig(
            faf_altitude_ft=6000,
            thr_elevation_ft=1922,
            faf_thr_distance_nm=12.2,
            tch_rdh_ft=49,
            oca_ft=2450,
            offset_enabled=True,
            offset_distance_nm=2.0,
        )
        steps = compute_steps(cfg)
        # d=0,1,2 dropped (display distance <= 0); d=2 -> 0.0 also dropped
        assert all(float(s.distance_label) > 0 for s in steps)
        assert len(steps) == 10  # d=3..12 survive


class TestStepsToNumericColumns:
    def test_maps_distance_label_to_publication_altitude(self):
        steps = compute_steps(REFERENCE_CFG)
        numeric = steps_to_numeric_columns(steps)
        assert numeric["12"] == "5940"
        assert numeric["0"] == str(next(s.publication_altitude_ft for s in steps if s.distance_label == "0"))


class TestComputeTable:
    def test_header_and_row_count(self):
        rows = compute_table(REFERENCE_CFG)
        assert rows[0][0] == "Distance from MAPt (NM)"
        assert len(rows) == 1 + 13  # header + 13 data rows

    def test_title_row_optional(self):
        rows = compute_table(REFERENCE_CFG, title="CDFA Table")
        assert rows[0] == ["CDFA Table", "", "", "", ""]
        assert rows[1][0] == "Distance from MAPt (NM)"


class TestValidation:
    def test_zero_distance_raises(self):
        cfg = DistAltConfig(
            faf_altitude_ft=6000,
            thr_elevation_ft=1922,
            faf_thr_distance_nm=0,
            tch_rdh_ft=49,
            oca_ft=2450,
        )
        with pytest.raises(ValueError):
            compute_summary(cfg)

    def test_negative_offset_raises(self):
        cfg = DistAltConfig(
            faf_altitude_ft=6000,
            thr_elevation_ft=1922,
            faf_thr_distance_nm=12.2,
            tch_rdh_ft=49,
            oca_ft=2450,
            offset_enabled=True,
            offset_distance_nm=-1,
        )
        with pytest.raises(ValueError):
            compute_steps(cfg)
