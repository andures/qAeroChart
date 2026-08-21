# -*- coding: utf-8 -*-
"""Unit tests for msa.py — pure math, no QGIS required."""
import math

from qAeroChart.core.msa import (
    MSASector,
    NM_TO_METERS,
    build_msa_sectors,
    build_sector_ring,
    resolve_true_bearing,
)


# ---------------------------------------------------------------------------
# resolve_true_bearing
# ---------------------------------------------------------------------------

class TestResolveTrueBearing:
    def test_true_outbound_passthrough(self):
        brg = resolve_true_bearing(90.0, is_magnetic=False, mag_var_signed=0.0, is_inbound=False)
        assert brg == 90.0

    def test_magnetic_east_variation_adds(self):
        brg = resolve_true_bearing(90.0, is_magnetic=True, mag_var_signed=5.0, is_inbound=False)
        assert abs(brg - 95.0) < 1e-9

    def test_magnetic_west_variation_subtracts(self):
        brg = resolve_true_bearing(90.0, is_magnetic=True, mag_var_signed=-5.0, is_inbound=False)
        assert abs(brg - 85.0) < 1e-9

    def test_inbound_reverses_180(self):
        brg = resolve_true_bearing(0.0, is_magnetic=False, mag_var_signed=0.0, is_inbound=True)
        assert abs(brg - 180.0) < 1e-9

    def test_wraps_to_0_360(self):
        brg = resolve_true_bearing(350.0, is_magnetic=True, mag_var_signed=20.0, is_inbound=False)
        assert abs(brg - 10.0) < 1e-9
        assert 0.0 <= brg < 360.0


# ---------------------------------------------------------------------------
# build_sector_ring
# ---------------------------------------------------------------------------

class TestBuildSectorRing:
    def test_ring_is_closed(self):
        ring = build_sector_ring(0.0, 0.0, 0.0, 90.0, 1000.0)
        assert ring[0] == ring[-1]

    def test_wedge_first_outer_point_matches_start_bearing(self):
        """start_true=0 (North) → first outer vertex should be due north of center."""
        ring = build_sector_ring(0.0, 0.0, 0.0, 90.0, 1000.0)
        x, y = ring[1]  # ring[0] is the center point for a plain wedge
        assert abs(x) < 1e-6
        assert abs(y - 1000.0) < 1e-6

    def test_wedge_includes_center_point(self):
        ring = build_sector_ring(0.0, 0.0, 0.0, 90.0, 1000.0)
        assert ring[0] == (0.0, 0.0)

    def test_donut_excludes_center_point(self):
        ring = build_sector_ring(0.0, 0.0, 0.0, 90.0, 1000.0, inner_r_m=500.0)
        assert (0.0, 0.0) not in ring

    def test_donut_has_outer_and_inner_vertices(self):
        ring = build_sector_ring(0.0, 0.0, 0.0, 90.0, 1000.0, inner_r_m=500.0)
        radii = [math.hypot(x, y) for x, y in ring]
        assert any(abs(r - 1000.0) < 1e-6 for r in radii)
        assert any(abs(r - 500.0) < 1e-6 for r in radii)

    def test_full_circle_seamless_closure(self):
        """start == end bearing should sweep a full 360° circle, closing without a gap."""
        ring = build_sector_ring(0.0, 0.0, 45.0, 45.0, 1000.0)
        # First and last arc vertices coincide (no visible slit for the full-circle case)
        assert math.hypot(ring[0][0] - ring[-1][0], ring[0][1] - ring[-1][1]) < 1e-6

    def test_full_circle_radii_constant(self):
        ring = build_sector_ring(0.0, 0.0, 0.0, 0.0, 1000.0)
        radii = [math.hypot(x, y) for x, y in ring]
        assert all(abs(r - 1000.0) < 1e-6 for r in radii)

    def test_full_circle_plain_wedge_has_no_center_point(self):
        """A full-circle plain wedge (inner radius 0) must not draw a spoke
        from the center — regression test for the ported-script bug where
        the ring always closed through the center point."""
        ring = build_sector_ring(0.0, 0.0, 0.0, 0.0, 1000.0)
        assert (0.0, 0.0) not in ring

    def test_wraparound_span(self):
        """A sector from 350° to 10° should sweep 20°, not -340°."""
        ring = build_sector_ring(0.0, 0.0, 350.0, 10.0, 1000.0)
        # last outer-arc vertex (before closing back to ring[0]) should sit near bearing 10°
        last_arc_pt = ring[-2]
        angle = math.degrees(math.atan2(last_arc_pt[0], last_arc_pt[1])) % 360.0
        assert abs(angle - 10.0) < 1.0


# ---------------------------------------------------------------------------
# build_msa_sectors
# ---------------------------------------------------------------------------

class TestBuildMsaSectors:
    def test_returns_one_geometry_per_sector(self):
        sectors = [
            MSASector(0, 90, 0, 25, 2500),
            MSASector(90, 180, 0, 25, 3000),
        ]
        results = build_msa_sectors(
            0.0, 0.0, sectors, is_magnetic=False, mag_var_signed=0.0, is_inbound=False,
        )
        assert len(results) == 2

    def test_outer_radius_converted_to_meters(self):
        sectors = [MSASector(0, 90, 0, 25, 2500)]
        results = build_msa_sectors(
            0.0, 0.0, sectors, is_magnetic=False, mag_var_signed=0.0, is_inbound=False,
        )
        radii = [math.hypot(x, y) for x, y in results[0].ring[1:-1]]
        assert all(abs(r - 25 * NM_TO_METERS) < 1.0 for r in radii)

    def test_preserves_original_sector_data(self):
        sectors = [MSASector(0, 90, 0, 25, 2500)]
        results = build_msa_sectors(
            0.0, 0.0, sectors, is_magnetic=False, mag_var_signed=0.0, is_inbound=False,
        )
        assert results[0].sector is sectors[0]

    def test_magnetic_and_inbound_applied_per_sector(self):
        sectors = [MSASector(90, 180, 0, 25, 2500)]
        results = build_msa_sectors(
            0.0, 0.0, sectors, is_magnetic=True, mag_var_signed=10.0, is_inbound=True,
        )
        # 90 -> inbound reverses to 270 -> +10 mag var = 280
        assert abs(results[0].start_true - 280.0) < 1e-9
        # 180 -> inbound reverses to 0 -> +10 mag var = 10
        assert abs(results[0].end_true - 10.0) < 1e-9
