"""
Small helpers that keep showing up everywhere.
Nothing fancy — just the stuff I got tired of rewriting.
"""

import math
import numpy as np
from typing import Tuple


# Earth radius in meters (WGS84 approx is fine for this)
EARTH_RADIUS = 6371000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS * math.asin(math.sqrt(a))


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing in degrees from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def destination_point(lat: float, lon: float, distance_m: float, bearing_deg: float) -> Tuple[float, float]:
    """Given a start point, distance and bearing, return the end lat/lon."""
    delta = distance_m / EARTH_RADIUS
    theta = math.radians(bearing_deg)
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)

    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), (math.degrees(lambda2) + 540) % 360 - 180


def latlon_to_local_xy(lat: float, lon: float, ref_lat: float, ref_lon: float) -> Tuple[float, float]:
    """
    Convert lat/lon to a local Cartesian frame (meters) centered on ref point.
    Good enough for airspace sizes under ~200 nm.
    """
    x = haversine_distance(ref_lat, ref_lon, ref_lat, lon) * (1 if lon >= ref_lon else -1)
    y = haversine_distance(ref_lat, ref_lon, lat, ref_lon) * (1 if lat >= ref_lat else -1)
    return x, y


def local_xy_to_latlon(x: float, y: float, ref_lat: float, ref_lon: float) -> Tuple[float, float]:
    """Inverse of the above."""
    dist = math.sqrt(x * x + y * y)
    brg = (math.degrees(math.atan2(x, y)) + 360) % 360
    return destination_point(ref_lat, ref_lon, dist, brg)


def knots_to_ms(knots: float) -> float:
    return knots * 0.514444


def ms_to_knots(ms: float) -> float:
    return ms / 0.514444


def feet_to_meters(ft: float) -> float:
    return ft * 0.3048


def meters_to_feet(m: float) -> float:
    return m / 0.3048


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def normalize_heading(h: float) -> float:
    return h % 360.0
