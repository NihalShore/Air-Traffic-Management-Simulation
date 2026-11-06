"""
Aircraft state and basic kinematics.
I kept the state vector simple so it's easy to dump / log / plot later.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import numpy as np

from .utils import (
    knots_to_ms,
    ms_to_knots,
    feet_to_meters,
    meters_to_feet,
    normalize_heading,
    destination_point,
    haversine_distance,
)


@dataclass
class Aircraft:
    callsign: str
    lat: float                     # degrees
    lon: float                     # degrees
    alt_ft: float                  # feet
    speed_kts: float               # true airspeed, knots
    heading: float                 # degrees true
    vertical_rate_fpm: float = 0.0 # feet per minute
    aircraft_type: str = "A320"
    weight_kg: float = 65000.0

    # history for plotting / post analysis
    history: List[Tuple[float, float, float, float]] = field(default_factory=list)  # t, lat, lon, alt

    # performance limits (very rough, type-dependent later)
    max_speed_kts: float = 450.0
    min_speed_kts: float = 140.0
    max_climb_fpm: float = 3000.0
    max_descent_fpm: float = -3000.0
    max_bank_deg: float = 30.0

    # flags used by the simulator
    resolved: bool = False
    resolution_cmd: Optional[str] = None

    def __post_init__(self):
        self.heading = normalize_heading(self.heading)

    @property
    def alt_m(self) -> float:
        return feet_to_meters(self.alt_ft)

    @property
    def speed_ms(self) -> float:
        return knots_to_ms(self.speed_kts)

    @property
    def vertical_rate_ms(self) -> float:
        return self.vertical_rate_fpm * 0.00508   # fpm → m/s

    def position_tuple(self) -> Tuple[float, float, float]:
        return (self.lat, self.lon, self.alt_ft)

    def record(self, t: float):
        """Append current state to history."""
        self.history.append((t, self.lat, self.lon, self.alt_ft))

    def apply_control(self, new_heading: Optional[float] = None,
                      new_speed_kts: Optional[float] = None,
                      new_vs_fpm: Optional[float] = None):
        """Simple direct assignment of control inputs (pilot / ATC command)."""
        if new_heading is not None:
            self.heading = normalize_heading(new_heading)
        if new_speed_kts is not None:
            self.speed_kts = float(np.clip(new_speed_kts, self.min_speed_kts, self.max_speed_kts))
        if new_vs_fpm is not None:
            self.vertical_rate_fpm = float(np.clip(new_vs_fpm, self.max_descent_fpm, self.max_climb_fpm))

    def step(self, dt: float, wind_n: float = 0.0, wind_e: float = 0.0):
        """
        Advance the aircraft by dt seconds.
        wind_n / wind_e are wind components in m/s (north, east).
        """
        # ground speed components
        tas_ms = self.speed_ms
        hdg_rad = np.radians(self.heading)

        # true airspeed vector
        vn = tas_ms * np.cos(hdg_rad)
        ve = tas_ms * np.sin(hdg_rad)

        # add wind
        gnd_vn = vn + wind_n
        gnd_ve = ve + wind_e

        # distance traveled over ground
        dist = np.sqrt(gnd_vn**2 + gnd_ve**2) * dt
        gnd_track = np.degrees(np.arctan2(gnd_ve, gnd_vn)) % 360

        # new position
        self.lat, self.lon = destination_point(self.lat, self.lon, dist, gnd_track)

        # altitude
        self.alt_ft += self.vertical_rate_fpm * (dt / 60.0)
        self.alt_ft = max(0.0, self.alt_ft)   # don't go underground

    def distance_to(self, other: "Aircraft") -> float:
        """Horizontal distance in meters."""
        return haversine_distance(self.lat, self.lon, other.lat, other.lon)

    def vertical_separation(self, other: "Aircraft") -> float:
        """Absolute vertical separation in feet."""
        return abs(self.alt_ft - other.alt_ft)

    def copy(self) -> "Aircraft":
        """Shallow-ish copy for what-if calculations."""
        a = Aircraft(
            callsign=self.callsign,
            lat=self.lat,
            lon=self.lon,
            alt_ft=self.alt_ft,
            speed_kts=self.speed_kts,
            heading=self.heading,
            vertical_rate_fpm=self.vertical_rate_fpm,
            aircraft_type=self.aircraft_type,
            weight_kg=self.weight_kg,
        )
        a.history = list(self.history)
        return a

    def __repr__(self):
        return (f"Aircraft({self.callsign}, "
                f"{self.lat:.4f},{self.lon:.4f}, "
                f"{self.alt_ft:.0f}ft, "
                f"{self.speed_kts:.0f}kts @{self.heading:.0f}°)")
