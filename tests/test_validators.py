# tests/test_validators.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from qAeroChart.utils.validators import Validators


# ── validate_coordinate ─────────────────────────────────────────────────────

class TestValidateCoordinate:
    def test_valid_number(self):
        ok, _msg, val = Validators.validate_coordinate(100.0)
        assert ok and val == pytest.approx(100.0)

    def test_projected_utm_x_not_rejected(self):
        """Projected UTM X ~ 500000 must NOT be rejected as out of range (B9)."""
        ok, msg, val = Validators.validate_coordinate(500000.0, "x")
        assert ok, f"Projected coordinate was wrongly rejected: {msg}"

    def test_projected_utm_y_not_rejected(self):
        ok, msg, val = Validators.validate_coordinate(1200000.0, "y")
        assert ok, f"Projected coordinate was wrongly rejected: {msg}"

    def test_negative_projected_accepted(self):
        ok, _msg, val = Validators.validate_coordinate(-300000.0, "x")
        assert ok and val == pytest.approx(-300000.0)

    def test_non_numeric_rejected(self):
        ok, _msg, val = Validators.validate_coordinate("not_a_number")
        assert not ok and val is None

    def test_none_rejected(self):
        ok, _msg, val = Validators.validate_coordinate(None)
        assert not ok and val is None


# ── validate_distance ────────────────────────────────────────────────────────

class TestValidateDistance:
    def test_valid_zero(self):
        ok, _msg, val = Validators.validate_distance(0)
        assert ok and val == pytest.approx(0.0)

    def test_valid_integer(self):
        ok, _msg, val = Validators.validate_distance(10)
        assert ok and val == pytest.approx(10.0)

    def test_valid_float_string(self):
        ok, _msg, val = Validators.validate_distance("6.5")
        assert ok and val == pytest.approx(6.5)

    def test_negative_rejected(self):
        ok, msg, val = Validators.validate_distance(-1)
        assert not ok
        assert val is None
        assert "negative" in msg.lower()

    def test_over_range_rejected(self):
        ok, _msg, val = Validators.validate_distance(1000)
        assert not ok
        assert val is None

    def test_non_numeric_rejected(self):
        ok, _msg, val = Validators.validate_distance("abc")
        assert not ok
        assert val is None

    def test_none_rejected(self):
        ok, _msg, val = Validators.validate_distance(None)
        assert not ok


# ── validate_elevation ───────────────────────────────────────────────────────

class TestValidateElevation:
    def test_valid_positive(self):
        ok, _msg, val = Validators.validate_elevation(500)
        assert ok and val == pytest.approx(500.0)

    def test_valid_zero(self):
        ok, _msg, val = Validators.validate_elevation(0)
        assert ok

    def test_valid_negative_dead_sea(self):
        ok, _msg, _val = Validators.validate_elevation(-1400)
        assert ok

    def test_too_low_rejected(self):
        ok, _msg, val = Validators.validate_elevation(-1501)
        assert not ok and val is None

    def test_too_high_rejected(self):
        ok, _msg, val = Validators.validate_elevation(60001)
        assert not ok and val is None

    def test_string_input(self):
        ok, _msg, val = Validators.validate_elevation("2000")
        assert ok and val == pytest.approx(2000.0)

    def test_non_numeric_rejected(self):
        ok, _msg, val = Validators.validate_elevation("high")
        assert not ok and val is None


# ── validate_runway_direction ────────────────────────────────────────────────

class TestValidateRunwayDirection:
    def test_valid_09_27(self):
        ok, _msg = Validators.validate_runway_direction("09/27")
        assert ok

    def test_valid_18_36(self):
        ok, _msg = Validators.validate_runway_direction("18/36")
        assert ok

    def test_valid_01_19(self):
        ok, _msg = Validators.validate_runway_direction("01/19")
        assert ok

    def test_non_reciprocal_rejected(self):
        ok, msg = Validators.validate_runway_direction("09/10")
        assert not ok
        assert "reciprocal" in msg.lower()

    def test_invalid_format_rejected(self):
        ok, _msg = Validators.validate_runway_direction("runway09")
        assert not ok

    def test_out_of_range_rejected(self):
        ok, _msg = Validators.validate_runway_direction("00/18")
        assert not ok

    def test_empty_rejected(self):
        ok, _msg = Validators.validate_runway_direction("")
        assert not ok

    def test_none_rejected(self):
        ok, _msg = Validators.validate_runway_direction(None)
        assert not ok


# ── validate_runway_length ───────────────────────────────────────────────────

class TestValidateRunwayLength:
    def test_valid_3000m(self):
        ok, _msg, val = Validators.validate_runway_length(3000)
        assert ok and val == pytest.approx(3000.0)

    def test_lower_boundary(self):
        ok, _msg, _val = Validators.validate_runway_length(100)
        assert ok

    def test_upper_boundary(self):
        ok, _msg, _val = Validators.validate_runway_length(6000)
        assert ok

    def test_too_short_rejected(self):
        ok, _msg, val = Validators.validate_runway_length(50)
        assert not ok and val is None

    def test_too_long_rejected(self):
        ok, _msg, val = Validators.validate_runway_length(10000)
        assert not ok and val is None

    def test_string_input(self):
        ok, _msg, val = Validators.validate_runway_length("2500")
        assert ok and val == pytest.approx(2500.0)

    def test_non_numeric_rejected(self):
        ok, _msg, val = Validators.validate_runway_length("long")
        assert not ok and val is None
