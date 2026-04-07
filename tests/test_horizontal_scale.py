"""Tests for the pure-Python horizontal scale geometry helper (Issue #69)."""
import pytest
from qAeroChart.core.horizontal_scale import horizontal_scale_tick_offsets

_FT_TO_M = 0.3048


class TestReturnStructure:
    def test_returns_expected_keys(self):
        result = horizontal_scale_tick_offsets()
        assert set(result.keys()) == {
            "m_pos_ticks", "m_neg_ticks",
            "m_pos_minor", "m_neg_minor",
            "ft_pos_ticks", "ft_neg_ticks",
            "ft_pos_minor", "ft_neg_minor",
            "half_spacing", "tick_length_m",
            "metre_right", "metre_left",
            "ft_right", "ft_left",
        }

    def test_half_spacing_is_half_tick_length(self):
        result = horizontal_scale_tick_offsets(tick_length_m=20.0)
        assert result["half_spacing"] == pytest.approx(10.0)

    def test_stored_meta_matches_params(self):
        result = horizontal_scale_tick_offsets(metre_right=1000, ft_right=3000)
        assert result["metre_right"] == 1000
        assert result["ft_right"] == 3000


class TestMetreTicks:
    def test_pos_ticks_start_at_zero(self):
        result = horizontal_scale_tick_offsets(metre_right=1000, metre_right_step=500)
        assert result["m_pos_ticks"][0] == pytest.approx(0.0)

    def test_pos_ticks_end_at_metre_right(self):
        result = horizontal_scale_tick_offsets(metre_right=2500, metre_right_step=500)
        assert result["m_pos_ticks"][-1] == pytest.approx(2500.0)

    def test_pos_tick_count(self):
        # range(0, 2501, 500) → 0, 500, 1000, 1500, 2000, 2500 → 6 entries
        result = horizontal_scale_tick_offsets(metre_right=2500, metre_right_step=500)
        assert len(result["m_pos_ticks"]) == 6

    def test_neg_ticks_start_at_first_step(self):
        result = horizontal_scale_tick_offsets(metre_left=400, metre_left_step=100)
        assert result["m_neg_ticks"][0] == pytest.approx(100.0)

    def test_neg_ticks_end_at_metre_left(self):
        result = horizontal_scale_tick_offsets(metre_left=400, metre_left_step=100)
        assert result["m_neg_ticks"][-1] == pytest.approx(400.0)

    def test_neg_tick_count(self):
        # range(100, 401, 100) → 100, 200, 300, 400 → 4 entries
        result = horizontal_scale_tick_offsets(metre_left=400, metre_left_step=100)
        assert len(result["m_neg_ticks"]) == 4


class TestFeetTicks:
    def test_pos_ticks_start_at_zero(self):
        result = horizontal_scale_tick_offsets(ft_right=8000, ft_right_step=1000)
        assert result["ft_pos_ticks"][0] == pytest.approx(0.0)

    def test_pos_ticks_are_converted_to_metres(self):
        result = horizontal_scale_tick_offsets(ft_right=1000, ft_right_step=1000)
        assert result["ft_pos_ticks"][-1] == pytest.approx(1000 * _FT_TO_M)

    def test_pos_tick_count(self):
        # range(0, 8001, 1000) → 0..8000 → 9 entries
        result = horizontal_scale_tick_offsets(ft_right=8000, ft_right_step=1000)
        assert len(result["ft_pos_ticks"]) == 9

    def test_neg_ticks_converted_to_metres(self):
        result = horizontal_scale_tick_offsets(ft_left=1000, ft_left_step=1000)
        assert result["ft_neg_ticks"][0] == pytest.approx(1000 * _FT_TO_M)

    def test_neg_tick_count(self):
        # range(100, 1001, 100) → 10 entries (default ft_left_step=100)
        result = horizontal_scale_tick_offsets(ft_left=1000, ft_left_step=100)
        assert len(result["ft_neg_ticks"]) == 10


class TestMinorTicks:
    def test_pos_minor_are_half_steps(self):
        result = horizontal_scale_tick_offsets(
            metre_right=1000, metre_right_step=500
        )
        # range(250, 1000, 500) → [250, 750]
        assert len(result["m_pos_minor"]) == 2
        assert result["m_pos_minor"][0] == pytest.approx(250.0)
        assert result["m_pos_minor"][1] == pytest.approx(750.0)

    def test_neg_minor_are_half_steps(self):
        result = horizontal_scale_tick_offsets(
            metre_left=200, metre_left_step=100
        )
        # range(50, 200, 100) → [50, 150]
        assert len(result["m_neg_minor"]) == 2
        assert result["m_neg_minor"][0] == pytest.approx(50.0)

    def test_ft_pos_minor_converted_to_metres(self):
        result = horizontal_scale_tick_offsets(
            ft_right=2000, ft_right_step=1000
        )
        # range(500, 2000, 1000) → [500 ft]
        assert result["ft_pos_minor"][0] == pytest.approx(500 * _FT_TO_M)


class TestEdgeCases:
    def test_zero_left_extent_gives_empty_neg_lists(self):
        result = horizontal_scale_tick_offsets(
            metre_left=0, metre_left_step=100,
            ft_left=0, ft_left_step=100,
        )
        assert result["m_neg_ticks"] == []
        assert result["ft_neg_ticks"] == []

    def test_custom_tick_length_stored(self):
        result = horizontal_scale_tick_offsets(tick_length_m=30.0)
        assert result["tick_length_m"] == pytest.approx(30.0)
        assert result["half_spacing"] == pytest.approx(15.0)
