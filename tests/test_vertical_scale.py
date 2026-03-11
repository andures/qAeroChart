"""Tests for the pure-Python vertical scale geometry helper (Task 2)."""
import pytest
from qAeroChart.core.vertical_scale import vertical_scale_tick_offsets

FT_TO_M = 0.3048
DEFAULT_VE = 10.0


class TestTickOffsetStructure:
    def test_returns_expected_keys(self):
        result = vertical_scale_tick_offsets()
        assert set(result.keys()) == {
            "metre_bases", "metre_tips", "feet_bases", "feet_tips", "connector",
            "metre_small_ticks", "feet_small_ticks", "half_spacing", "sec_offset",
        }

    def test_metre_count_default(self):
        # range(0, 101, 25) → [0, 25, 50, 75, 100] → 5 entries
        result = vertical_scale_tick_offsets()
        assert len(result["metre_bases"]) == 5
        assert len(result["metre_tips"]) == 5

    def test_feet_count_default(self):
        # range(0, 301, 50) → [0, 50, 100, 150, 200, 250, 300] → 7 entries
        result = vertical_scale_tick_offsets()
        assert len(result["feet_bases"]) == 7
        assert len(result["feet_tips"]) == 7

    def test_connector_is_two_element_tuple(self):
        result = vertical_scale_tick_offsets()
        assert len(result["connector"]) == 2


class TestMetreTickPositions:
    def test_first_metre_base_at_origin(self):
        result = vertical_scale_tick_offsets()
        along, perp = result["metre_bases"][0]
        assert along == pytest.approx(0.0)
        assert perp == pytest.approx(0.0)

    def test_metre_base_spacing_equals_step_times_ve(self):
        # step=25, VE=10 → 250m between consecutive ticks
        result = vertical_scale_tick_offsets(metre_step=25, vertical_exaggeration=10.0)
        alongs = [t[0] for t in result["metre_bases"]]
        assert alongs[1] - alongs[0] == pytest.approx(25 * 10.0)

    def test_metre_tips_perp_positive(self):
        result = vertical_scale_tick_offsets(tick_length_m=15.0)
        for _, perp in result["metre_tips"]:
            assert perp == pytest.approx(15.0)

    def test_metre_bases_perp_zero(self):
        result = vertical_scale_tick_offsets()
        for _, perp in result["metre_bases"]:
            assert perp == pytest.approx(0.0)

    def test_last_metre_base_along(self):
        # metre_max=100, VE=10 → 1000m
        result = vertical_scale_tick_offsets(metre_max=100, vertical_exaggeration=10.0)
        along, _ = result["metre_bases"][-1]
        assert along == pytest.approx(100 * 10.0)


class TestFeetTickPositions:
    def test_first_feet_base_at_origin(self):
        result = vertical_scale_tick_offsets()
        along, perp = result["feet_bases"][0]
        assert along == pytest.approx(0.0)
        assert perp == pytest.approx(0.0)

    def test_feet_tips_perp_negative(self):
        # feet ticks go the opposite side from metre ticks
        result = vertical_scale_tick_offsets(tick_length_m=15.0)
        for _, perp in result["feet_tips"]:
            assert perp == pytest.approx(-15.0)

    def test_feet_bases_perp_zero(self):
        result = vertical_scale_tick_offsets()
        for _, perp in result["feet_bases"]:
            assert perp == pytest.approx(0.0)


class TestDualRailExtensions:
    """Tests for dual-rail, mid-step ticks, and scale_denominator (Task 2b-2)."""

    def test_half_spacing_in_result(self):
        r = vertical_scale_tick_offsets()
        assert "half_spacing" in r
        assert r["half_spacing"] == pytest.approx(15.0 * 0.5)

    def test_sec_offset_in_result(self):
        r = vertical_scale_tick_offsets()
        assert "sec_offset" in r
        assert r["sec_offset"] == pytest.approx(15.0 * 0.8)

    def test_metre_small_ticks_key_exists(self):
        r = vertical_scale_tick_offsets()
        assert "metre_small_ticks" in r

    def test_feet_small_ticks_key_exists(self):
        r = vertical_scale_tick_offsets()
        assert "feet_small_ticks" in r

    def test_metre_small_tick_count_default(self):
        # range(25//2, 100, 25) = range(12, 100, 25) = [12, 37, 62, 87] → 4
        r = vertical_scale_tick_offsets(metre_max=100, metre_step=25)
        assert len(r["metre_small_ticks"]) == 4

    def test_feet_small_tick_count_default(self):
        # range(50//2, 300, 50) = range(25, 300, 50) = [25, 75, ..., 275] → 6
        r = vertical_scale_tick_offsets(feet_max=300, feet_step=50)
        assert len(r["feet_small_ticks"]) == 6

    def test_metre_small_tick_first_along(self):
        # first mid-step = (metre_step // 2) * VE
        r = vertical_scale_tick_offsets(metre_step=25, vertical_exaggeration=10.0)
        along, _ = r["metre_small_ticks"][0]
        assert along == pytest.approx((25 // 2) * 10.0)

    def test_feet_small_tick_first_along(self):
        # first mid-step = (feet_step // 2) * FT_TO_M * VE
        r = vertical_scale_tick_offsets(feet_step=50, vertical_exaggeration=10.0)
        along, _ = r["feet_small_ticks"][0]
        assert along == pytest.approx((50 // 2) * FT_TO_M * 10.0)

    def test_small_tick_perps_are_zero(self):
        r = vertical_scale_tick_offsets()
        for _, perp in r["metre_small_ticks"]:
            assert perp == pytest.approx(0.0)
        for _, perp in r["feet_small_ticks"]:
            assert perp == pytest.approx(0.0)

    def test_scale_denominator_affects_metre_along(self):
        r1 = vertical_scale_tick_offsets(scale_denominator=10000)
        r2 = vertical_scale_tick_offsets(scale_denominator=5000)
        # VE=10 vs VE=5 → alongs are twice as large with 10000
        assert r1["metre_bases"][1][0] == pytest.approx(r2["metre_bases"][1][0] * 2)

    def test_scale_denominator_10000_equals_ve_10(self):
        r1 = vertical_scale_tick_offsets(vertical_exaggeration=10.0)
        r2 = vertical_scale_tick_offsets(scale_denominator=10000)
        assert r1["metre_bases"][1][0] == pytest.approx(r2["metre_bases"][1][0])

    def test_half_spacing_custom_tick_length(self):
        r = vertical_scale_tick_offsets(tick_length_m=20.0)
        assert r["half_spacing"] == pytest.approx(20.0 * 0.5)
        assert r["sec_offset"] == pytest.approx(20.0 * 0.8)

    def test_second_feet_base_along(self):
        # i=50 ft → 50 * 0.3048 * 10 = 152.4m
        result = vertical_scale_tick_offsets(feet_step=50, vertical_exaggeration=10.0)
        along, _ = result["feet_bases"][1]
        assert along == pytest.approx(50 * FT_TO_M * 10.0)

    def test_last_feet_base_along(self):
        # feet_max=300, VE=10 → 300 * 0.3048 * 10 = 914.4m
        result = vertical_scale_tick_offsets(feet_max=300, vertical_exaggeration=10.0)
        along, _ = result["feet_bases"][-1]
        assert along == pytest.approx(300 * FT_TO_M * 10.0)


class TestConnector:
    def test_connector_metre_end_matches_last_metre_base(self):
        result = vertical_scale_tick_offsets()
        metre_end, _ = result["connector"]
        assert metre_end == pytest.approx(result["metre_bases"][-1][0])

    def test_connector_feet_end_matches_last_feet_base(self):
        result = vertical_scale_tick_offsets()
        _, feet_end = result["connector"]
        assert feet_end == pytest.approx(result["feet_bases"][-1][0])


class TestCustomParameters:
    def test_custom_ve_scales_metre_positions(self):
        result = vertical_scale_tick_offsets(metre_step=25, vertical_exaggeration=5.0)
        alongs = [t[0] for t in result["metre_bases"]]
        assert alongs[1] == pytest.approx(25 * 5.0)

    def test_custom_tick_length(self):
        result = vertical_scale_tick_offsets(tick_length_m=20.0)
        _, perp = result["metre_tips"][0]
        assert perp == pytest.approx(20.0)

    def test_custom_metre_max_count(self):
        result = vertical_scale_tick_offsets(metre_max=50, metre_step=25)
        # range(0, 51, 25) → [0, 25, 50] → 3
        assert len(result["metre_bases"]) == 3

    def test_custom_feet_max_count(self):
        result = vertical_scale_tick_offsets(feet_max=100, feet_step=50)
        # range(0, 101, 50) → [0, 50, 100] → 3
        assert len(result["feet_bases"]) == 3
