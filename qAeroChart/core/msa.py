# -*- coding: utf-8 -*-
"""
MSA (Minimum Sector Altitude) donut/sector geometry calculator.

Pure Python — no QGIS imports. Builds annular-sector polygon rings (donut
wedges, plain wedges, and full circles) around a center point, given bearings
expressed relative to magnetic or true north and inbound/outbound convention.
All distances in nautical miles, angles in degrees, coordinates in map CRS
units (meters).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

NM_TO_METERS = 1852.0


@dataclass
class MSASector:
    """One MSA ring/wedge, as entered by the user (input bearings, NM radii)."""

    start_brg: float
    end_brg: float
    inner_r_nm: float
    outer_r_nm: float
    altitude_ft: float


@dataclass
class MSASectorGeometry:
    """Computed polygon ring for one MSASector, plus the true bearings used to build it."""

    ring: list[tuple[float, float]]
    start_true: float
    end_true: float
    sector: MSASector


def resolve_true_bearing(
    input_brg: float, *, is_magnetic: bool, mag_var_signed: float, is_inbound: bool
) -> float:
    """Convert a user-entered bearing to a true bearing in degrees 0-360.

    ``is_inbound`` reverses the bearing 180° first (bearings TO the station are
    stored as the reciprocal outbound-FROM bearing before the sector is drawn).
    ``mag_var_signed`` is already signed (positive = East, negative = West) —
    callers own the E/W → sign conversion.
    """
    brg = (input_brg + 180.0) % 360.0 if is_inbound else input_brg
    if is_magnetic:
        brg = (brg + mag_var_signed) % 360.0
    return brg % 360.0


def build_sector_ring(
    center_x: float,
    center_y: float,
    start_true: float,
    end_true: float,
    outer_r_m: float,
    inner_r_m: float = 0.0,
) -> list[tuple[float, float]]:
    """Build a closed polygon ring for one annular sector (donut wedge).

    Sweeps clockwise from ``start_true`` to ``end_true`` (compass bearings,
    0°=North). A full circle (``start_true == end_true``) is handled without a
    special case: the arc's first and last vertices coincide, so the ring
    closes seamlessly. When ``inner_r_m`` is 0 the ring is a plain wedge (or
    full circle) fanning out from the center point instead of a donut.
    """
    span = (end_true - start_true) % 360.0
    if span == 0.0:
        span = 360.0
    steps = max(8, round(span / 3.0))

    start_rad = math.radians(90.0 - start_true)
    span_rad = math.radians(span)

    def _arc(radius_m: float) -> list[tuple[float, float]]:
        pts = []
        for i in range(steps + 1):
            angle = start_rad - span_rad * (i / steps)
            pts.append((
                center_x + radius_m * math.cos(angle),
                center_y + radius_m * math.sin(angle),
            ))
        return pts

    outer_pts = _arc(outer_r_m)
    if inner_r_m > 0.0:
        inner_pts = list(reversed(_arc(inner_r_m)))
        return outer_pts + inner_pts + [outer_pts[0]]
    return [(center_x, center_y)] + outer_pts + [(center_x, center_y)]


def build_msa_sectors(
    center_x: float,
    center_y: float,
    sectors: list[MSASector],
    *,
    is_magnetic: bool,
    mag_var_signed: float,
    is_inbound: bool,
) -> list[MSASectorGeometry]:
    """Compute the polygon ring for every sector around one center point."""
    results = []
    for sector in sectors:
        start_true = resolve_true_bearing(
            sector.start_brg, is_magnetic=is_magnetic,
            mag_var_signed=mag_var_signed, is_inbound=is_inbound,
        )
        end_true = resolve_true_bearing(
            sector.end_brg, is_magnetic=is_magnetic,
            mag_var_signed=mag_var_signed, is_inbound=is_inbound,
        )
        ring = build_sector_ring(
            center_x, center_y, start_true, end_true,
            sector.outer_r_nm * NM_TO_METERS,
            sector.inner_r_nm * NM_TO_METERS,
        )
        results.append(MSASectorGeometry(
            ring=ring, start_true=start_true, end_true=end_true, sector=sector,
        ))
    return results
