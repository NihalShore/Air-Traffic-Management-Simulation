"""
4D trajectory representation.
A trajectory is just a time-ordered list of states.
We keep both the discrete points and a simple linear interpolator.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np

from .utils import haversine_distance, latlon_to_local_xy


@dataclass
class TrajectoryPoint:
    t: float          # seconds from sim start
    lat: float
    lon: float
    alt_ft: float
    speed_kts: float = 0.0
    heading: float = 0.0


class Trajectory4D:
    """
    Container for a full 4D path of one aircraft.
    Can be built from live simulation history or from a planned route.
    """

    def __init__(self, callsign: str = ""):
        self.callsign = callsign
        self.points: List[TrajectoryPoint] = []

    def add(self, t: float, lat: float, lon: float, alt_ft: float,
            speed_kts: float = 0.0, heading: float = 0.0):
        self.points.append(TrajectoryPoint(t, lat, lon, alt_ft, speed_kts, heading))

    def from_aircraft_history(self, aircraft):
        """Populate from the history list that Aircraft keeps."""
        self.callsign = aircraft.callsign
        self.points.clear()
        for t, lat, lon, alt in aircraft.history:
            self.points.append(TrajectoryPoint(t, lat, lon, alt))

    def duration(self) -> float:
        if len(self.points) < 2:
            return 0.0
        return self.points[-1].t - self.points[0].t

    def sample(self, t: float) -> Optional[TrajectoryPoint]:
        """Linear interpolation between the two surrounding points."""
        if not self.points:
            return None
        if t <= self.points[0].t:
            return self.points[0]
        if t >= self.points[-1].t:
            return self.points[-1]

        for i in range(len(self.points) - 1):
            p0, p1 = self.points[i], self.points[i + 1]
            if p0.t <= t <= p1.t:
                alpha = (t - p0.t) / (p1.t - p0.t + 1e-9)
                return TrajectoryPoint(
                    t=t,
                    lat=p0.lat + alpha * (p1.lat - p0.lat),
                    lon=p0.lon + alpha * (p1.lon - p0.lon),
                    alt_ft=p0.alt_ft + alpha * (p1.alt_ft - p0.alt_ft),
                    speed_kts=p0.speed_kts + alpha * (p1.speed_kts - p0.speed_kts),
                    heading=p0.heading,   # not interpolating heading for now
                )
        return None

    def horizontal_path(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return arrays of lat, lon for plotting."""
        if not self.points:
            return np.array([]), np.array([])
        lats = np.array([p.lat for p in self.points])
        lons = np.array([p.lon for p in self.points])
        return lats, lons

    def altitude_profile(self) -> Tuple[np.ndarray, np.ndarray]:
        ts = np.array([p.t for p in self.points])
        alts = np.array([p.alt_ft for p in self.points])
        return ts, alts

    def total_distance_nm(self) -> float:
        """Approximate ground track distance in nautical miles."""
        if len(self.points) < 2:
            return 0.0
        dist_m = 0.0
        for i in range(len(self.points) - 1):
            dist_m += haversine_distance(
                self.points[i].lat, self.points[i].lon,
                self.points[i + 1].lat, self.points[i + 1].lon
            )
        return dist_m / 1852.0

    def __len__(self):
        return len(self.points)

    def __repr__(self):
        return f"Trajectory4D({self.callsign}, {len(self.points)} pts, {self.duration():.0f}s)"
