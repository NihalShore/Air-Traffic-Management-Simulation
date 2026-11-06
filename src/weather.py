"""
Simple weather field.
For a student project we don't need a full NWP model — a wind grid plus
some turbulence is enough to show the effect on trajectories and conflict timing.
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass
class WeatherSample:
    wind_n: float   # m/s, positive north
    wind_e: float   # m/s, positive east
    wind_speed_kts: float
    wind_dir_deg: float
    turbulence: float  # 0–1, rough intensity


class WeatherField:
    """
    Analytic wind field + optional random turbulence.
    You can replace the wind function with real GRIB data later if you want.
    """

    def __init__(self,
                 base_wind_speed_kts: float = 25.0,
                 base_wind_dir_deg: float = 270.0,   # from the west
                 shear_strength: float = 0.002,      # (m/s) / m altitude
                 turbulence_intensity: float = 0.15,
                 seed: int = 42):
        self.base_speed = base_wind_speed_kts * 0.514444   # → m/s
        self.base_dir = np.radians(base_wind_dir_deg)
        self.shear = shear_strength
        self.turb_intensity = turbulence_intensity
        self.rng = np.random.default_rng(seed)

        # pre-compute base components
        self._base_n = self.base_speed * np.cos(self.base_dir)
        self._base_e = self.base_speed * np.sin(self.base_dir)

    def sample(self, lat: float, lon: float, alt_m: float, t: float = 0.0) -> WeatherSample:
        """
        Return wind at a given position and time.
        Right now the field is only altitude-dependent + a slow time variation.
        """
        # altitude shear (simple linear)
        shear_factor = 1.0 + self.shear * (alt_m - 5000.0)
        wind_n = self._base_n * shear_factor
        wind_e = self._base_e * shear_factor

        # mild temporal variation so trajectories aren't perfectly deterministic
        wind_n += 2.0 * np.sin(0.0003 * t + 0.1 * lat)
        wind_e += 1.5 * np.cos(0.0004 * t + 0.05 * lon)

        # turbulence (zero-mean noise scaled by intensity)
        if self.turb_intensity > 0:
            turb = self.rng.normal(0.0, self.turb_intensity * self.base_speed, size=2)
            wind_n += turb[0]
            wind_e += turb[1]

        speed = np.sqrt(wind_n**2 + wind_e**2)
        direction = (np.degrees(np.arctan2(wind_e, wind_n)) + 360) % 360

        return WeatherSample(
            wind_n=wind_n,
            wind_e=wind_e,
            wind_speed_kts=speed / 0.514444,
            wind_dir_deg=direction,
            turbulence=self.turb_intensity,
        )

    def wind_at_aircraft(self, aircraft, t: float = 0.0) -> Tuple[float, float]:
        """Convenience: return (wind_n, wind_e) in m/s."""
        s = self.sample(aircraft.lat, aircraft.lon, aircraft.alt_m, t)
        return s.wind_n, s.wind_e

    def set_wind(self, speed_kts: float, direction_deg: float):
        """Change the background wind on the fly."""
        self.base_speed = speed_kts * 0.514444
        self.base_dir = np.radians(direction_deg)
        self._base_n = self.base_speed * np.cos(self.base_dir)
        self._base_e = self.base_speed * np.sin(self.base_dir)
