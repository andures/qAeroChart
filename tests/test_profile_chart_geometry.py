# tests/test_profile_chart_geometry.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tests.mocks.qgis_mock  # noqa: F401

import pytest
from qAeroChart.core.profile_chart_geometry import ProfileChartGeometry
from tests.mocks.qgis_mock import _QgsPointXY as QgsPointXY

ORIGIN = QgsPointXY(0.0, 0.0)
NM = 1852.0
FT = 0.3048


# ── Unit conversion ──────────────────────────────────────────────────────────

def test_nm_to_meters_one():
    geom = ProfileChartGeometry(ORIGIN)
    assert geom.nm_to_meters(1.0) == pytest.approx(1852.0)


def test_nm_to_meters_zero():
    geom = ProfileChartGeometry(ORIGIN)
    assert geom.nm_to_meters(0.0) == pytest.approx(0.0)


def test_nm_to_meters_fractional():
    geom = ProfileChartGeometry(ORIGIN)
    assert geom.nm_to_meters(2.5) == pytest.approx(4630.0)


# ── calculate_profile_point ──────────────────────────────────────────────────

def test_profile_point_at_origin():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    pt = geom.calculate_profile_point(0.0, 0.0)
    assert pt.x() == pytest.approx(0.0)
    assert pt.y() == pytest.approx(0.0)


def test_profile_point_distance_only():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    pt = geom.calculate_profile_point(1.0, 0.0)
    assert pt.x() == pytest.approx(NM)
    assert pt.y() == pytest.approx(0.0)


def test_profile_point_elevation_only():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    pt = geom.calculate_profile_point(0.0, 1000.0)
    assert pt.x() == pytest.approx(0.0)
    assert pt.y() == pytest.approx(1000.0 * FT)


def test_vertical_exaggeration_applied():
    geom_1x = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    geom_10x = ProfileChartGeometry(ORIGIN, vertical_exaggeration=10.0)
    pt_1x = geom_1x.calculate_profile_point(0.0, 1000.0)
    pt_10x = geom_10x.calculate_profile_point(0.0, 1000.0)
    assert pt_10x.y() == pytest.approx(pt_1x.y() * 10.0)


def test_direction_right_to_left():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0, horizontal_direction=-1)
    pt = geom.calculate_profile_point(1.0, 0.0)
    assert pt.x() == pytest.approx(-NM)


def test_direction_left_to_right():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0, horizontal_direction=1)
    pt = geom.calculate_profile_point(1.0, 0.0)
    assert pt.x() == pytest.approx(NM)


def test_direction_right_to_left_large_negative():
    """Any negative value must give dir_sign=-1 (B8)."""
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0, horizontal_direction=-5)
    assert geom.dir_sign == -1


def test_direction_left_to_right_large_positive():
    """Any positive value must give dir_sign=+1 (B8)."""
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0, horizontal_direction=5)
    assert geom.dir_sign == 1


def test_origin_offset_preserved():
    origin = QgsPointXY(500.0, 300.0)
    geom = ProfileChartGeometry(origin, vertical_exaggeration=1.0)
    pt = geom.calculate_profile_point(0.0, 0.0)
    assert pt.x() == pytest.approx(500.0)
    assert pt.y() == pytest.approx(300.0)


# ── create_runway_line ───────────────────────────────────────────────────────

def test_runway_line_returns_two_points():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    pts = geom.create_runway_line(3000.0)
    assert len(pts) == 2


def test_runway_line_end_at_origin():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    _start, end = geom.create_runway_line(3000.0)
    assert end.x() == pytest.approx(ORIGIN.x())


def test_runway_line_start_before_origin():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    start, _end = geom.create_runway_line(3000.0)
    assert start.x() == pytest.approx(ORIGIN.x() - 3000.0)


def test_runway_line_on_baseline():
    origin = QgsPointXY(100.0, 200.0)
    geom = ProfileChartGeometry(origin, vertical_exaggeration=1.0)
    pts = geom.create_runway_line(1000.0)
    for pt in pts:
        assert pt.y() == pytest.approx(200.0)


# ── create_profile_line ──────────────────────────────────────────────────────

def test_profile_line_sorted_by_distance():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    points = [
        {"distance_nm": 3.0,  "elevation_ft": 1500.0, "point_name": "IF"},
        {"distance_nm": 0.0,  "elevation_ft": 500.0,  "point_name": "MAPt"},
        {"distance_nm": 6.0,  "elevation_ft": 2000.0, "point_name": "FAF"},
    ]
    line = geom.create_profile_line(points)
    assert len(line) == 3
    xs = [pt.x() for pt in line]
    assert xs == sorted(xs)


def test_profile_line_skips_invalid_elevation():
    # Invalid elevation_ft causes ValueError inside the per-point try/except.
    # distance_nm must be valid so the initial sort doesn't raise.
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    points = [
        {"distance_nm": 1.0, "elevation_ft": "not_a_number", "point_name": "bad"},
        {"distance_nm": 2.0, "elevation_ft": 600.0,           "point_name": "ok"},
    ]
    line = geom.create_profile_line(points)
    assert len(line) == 1


# ── create_distance_markers ──────────────────────────────────────────────────

def test_distance_markers_count():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    markers = geom.create_distance_markers(5.0)
    assert len(markers) == 6  # 0, 1, 2, 3, 4, 5


def test_distance_markers_labels():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    markers = geom.create_distance_markers(3.0)
    labels = [m["label"] for m in markers]
    assert labels == ["0", "1", "2", "3"]


def test_distance_markers_have_geometry():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    markers = geom.create_distance_markers(2.0)
    for m in markers:
        assert "geometry" in m
        assert len(m["geometry"]) == 2


# ── create_oca_box ───────────────────────────────────────────────────────────

def test_oca_box_is_closed_polygon():
    geom = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    poly = geom.create_oca_box(0.0, 2.0, 1000.0)
    assert len(poly) == 5
    assert poly[0].x() == pytest.approx(poly[-1].x())
    assert poly[0].y() == pytest.approx(poly[-1].y())


def test_oca_box_height_scaled():
    geom_1x = ProfileChartGeometry(ORIGIN, vertical_exaggeration=1.0)
    geom_5x = ProfileChartGeometry(ORIGIN, vertical_exaggeration=5.0)
    top_1x = geom_1x.create_oca_box(0.0, 1.0, 1000.0)[2]  # top_right
    top_5x = geom_5x.create_oca_box(0.0, 1.0, 1000.0)[2]
    assert top_5x.y() == pytest.approx(top_1x.y() * 5.0)
