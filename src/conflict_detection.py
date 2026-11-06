"""
Conflict detection.

I use a classic CPA (closest point of approach) approach in a local
Cartesian frame.  It's fast, easy to understand, and good enough for
a few dozen aircraft.  For real ATC you'd add time filters, uncertainty
ellipsoids, etc., but this already shows the core idea.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from .aircraft import Aircraft
from .utils import latlon_to_local_xy, haversine_distance


# Standard ICAO-ish separation minima (can be changed per airspace)
HORIZONTAL_SEP_NM = 5.0          # nm
VERTICAL_SEP_FT = 1000.0         # ft
LOOKAHEAD_SEC = 300.0            # how far ahead we look for conflicts


@dataclass
class Conflict:
    ac1: str
    ac2: str
    t_cpa: float                 # seconds from now
    dist_cpa_nm: float           # horizontal distance at CPA
    vert_sep_ft: float           # vertical separation at CPA
    severity: float              # 0–1, higher = worse
    lat_cpa: float = 0.0
    lon_cpa: float = 0.0

    def __repr__(self):
        return (f"Conflict({self.ac1}\u2194{self.ac2}, "
                f"CPA in {self.t_cpa:.0f}s, "
                f"{self.dist_cpa_nm:.1f} nm / {self.vert_sep_ft:.0f} ft)")


class ConflictDetector:
    def __init__(self,
                 h_sep_nm: float = HORIZONTAL_SEP_NM,
                 v_sep_ft: float = VERTICAL_SEP_FT,
                 lookahead: float = LOOKAHEAD_SEC):
        self.h_sep_m = h_sep_nm * 1852.0
        self.v_sep_ft = v_sep_ft
        self.lookahead = lookahead

    def _relative_cpa(self, ac1: Aircraft, ac2: Aircraft,
                      ref_lat: float, ref_lon: float) -> Tuple[float, float, float]:
        """
        Returns (time_to_cpa, horizontal_dist_at_cpa, vertical_sep_at_cpa).
        Negative time means CPA is in the past.
        """
        # positions in local frame
        x1, y1 = latlon_to_local_xy(ac1.lat, ac1.lon, ref_lat, ref_lon)
        x2, y2 = latlon_to_local_xy(ac2.lat, ac2.lon, ref_lat, ref_lon)

        # velocities (ground speed approx — we ignore wind here for simplicity)
        h1 = np.radians(ac1.heading)
        h2 = np.radians(ac2.heading)
        v1n = ac1.speed_ms * np.cos(h1)
        v1e = ac1.speed_ms * np.sin(h1)
        v2n = ac2.speed_ms * np.cos(h2)
        v2e = ac2.speed_ms * np.sin(h2)

        # relative position and velocity
        dx = x2 - x1
        dy = y2 - y1
        dvx = v2e - v1e
        dvy = v2n - v1n

        # time of closest approach
        dv2 = dvx*dvx + dvy*dvy
        if dv2 < 1e-6:
            t_cpa = 0.0
        else:
            t_cpa = - (dx*dvx + dy*dvy) / dv2

        # position at CPA
        cpa_x = dx + dvx * t_cpa
        cpa_y = dy + dvy * t_cpa
        dist_cpa = np.sqrt(cpa_x*cpa_x + cpa_y*cpa_y)

        # vertical
        # assume constant vertical rates
        alt1_cpa = ac1.alt_ft + ac1.vertical_rate_fpm * (t_cpa / 60.0)
        alt2_cpa = ac2.alt_ft + ac2.vertical_rate_fpm * (t_cpa / 60.0)
        vert_sep = abs(alt1_cpa - alt2_cpa)

        return t_cpa, dist_cpa, vert_sep

    def check_pair(self, ac1: Aircraft, ac2: Aircraft) -> Optional[Conflict]:
        if ac1.callsign == ac2.callsign:
            return None

        # use midpoint as reference for local frame
        ref_lat = (ac1.lat + ac2.lat) / 2
        ref_lon = (ac1.lon + ac2.lon) / 2

        t_cpa, dist_m, vert_ft = self._relative_cpa(ac1, ac2, ref_lat, ref_lon)

        # only care about future CPA inside the lookahead window
        if t_cpa < 0 or t_cpa > self.lookahead:
            return None

        # is it actually a loss of separation?
        h_loss = dist_m < self.h_sep_m
        v_loss = vert_ft < self.v_sep_ft

        if not (h_loss and v_loss):
            return None

        # severity: how deep into the protected zone we go
        h_ratio = dist_m / self.h_sep_m
        v_ratio = vert_ft / self.v_sep_ft
        severity = 1.0 - min(h_ratio, v_ratio)
        severity = max(0.0, min(1.0, severity))

        return Conflict(
            ac1=ac1.callsign,
            ac2=ac2.callsign,
            t_cpa=t_cpa,
            dist_cpa_nm=dist_m / 1852.0,
            vert_sep_ft=vert_ft,
            severity=severity,
        )

    def detect(self, aircraft: List[Aircraft]) -> List[Conflict]:
        """Check every pair.  O(n\u00b2) but fine for student-scale scenarios."""
        conflicts = []
        n = len(aircraft)
        for i in range(n):
            for j in range(i + 1, n):
                c = self.check_pair(aircraft[i], aircraft[j])
                if c is not None:
                    conflicts.append(c)
        # sort by soonest CPA
        conflicts.sort(key=lambda c: c.t_cpa)
        return conflicts

    def current_separation(self, ac1: Aircraft, ac2: Aircraft) -> Tuple[float, float]:
        """Instantaneous horizontal (nm) and vertical (ft) separation."""
        h = haversine_distance(ac1.lat, ac1.lon, ac2.lat, ac2.lon) / 1852.0
        v = abs(ac1.alt_ft - ac2.alt_ft)
        return h, v
