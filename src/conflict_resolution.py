"""
Conflict resolution.

A few simple but realistic ATC-style manoeuvres:
  - vertical (climb / descend)
  - horizontal (heading change)
  - speed change

We evaluate a small set of candidates and pick the one that resolves
the conflict with the least cost (time / fuel / passenger comfort).
This is deliberately not optimal — real systems use more sophisticated
search or optimisation — but it demonstrates the idea cleanly.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import copy
import numpy as np

from .aircraft import Aircraft
from .conflict_detection import ConflictDetector, Conflict
from .utils import normalize_heading


@dataclass
class Resolution:
    callsign: str
    manoeuvre: str          # "climb", "descend", "left", "right", "speed_up", "slow_down"
    value: float            # new heading, new vs, or new speed
    cost: float             # lower is better
    resolved: bool = False

    def __repr__(self):
        return f"Resolution({self.callsign}: {self.manoeuvre} → {self.value:.0f}, cost={self.cost:.1f})"


class ConflictResolver:
    def __init__(self, detector: Optional[ConflictDetector] = None):
        self.detector = detector or ConflictDetector()
        # candidate deltas we try
        self.heading_deltas = [-30, -20, -15, 15, 20, 30]
        self.vs_options = [1500, 2000, -1500, -2000]   # fpm
        self.speed_deltas = [30, 40, -30, -40]         # kts

    def _simulate_pair(self, ac1: Aircraft, ac2: Aircraft,
                       duration: float = 180.0, dt: float = 5.0) -> bool:
        """
        Crude forward simulation of two aircraft for `duration` seconds.
        Returns True if a conflict still exists somewhere in the window.
        """
        a = ac1.copy()
        b = ac2.copy()
        t = 0.0
        while t < duration:
            a.step(dt)
            b.step(dt)
            t += dt
            # check instantaneous separation
            h, v = self.detector.current_separation(a, b)
            if h < 5.0 and v < 1000.0:
                return True   # still in conflict
        return False

    def generate_candidates(self, own: Aircraft, other: Aircraft) -> List[Resolution]:
        """Create a list of possible manoeuvres for `own`."""
        cands = []

        # vertical
        for vs in self.vs_options:
            # don't ask for a climb if already near ceiling, etc. — keep simple
            cands.append(Resolution(
                callsign=own.callsign,
                manoeuvre="climb" if vs > 0 else "descend",
                value=vs,
                cost=abs(vs) / 1000.0 + 1.0,   # vertical changes are a bit expensive
            ))

        # heading
        for d in self.heading_deltas:
            new_hdg = normalize_heading(own.heading + d)
            cands.append(Resolution(
                callsign=own.callsign,
                manoeuvre="left" if d < 0 else "right",
                value=new_hdg,
                cost=abs(d) / 10.0,
            ))

        # speed
        for ds in self.speed_deltas:
            new_spd = own.speed_kts + ds
            if own.min_speed_kts <= new_spd <= own.max_speed_kts:
                cands.append(Resolution(
                    callsign=own.callsign,
                    manoeuvre="speed_up" if ds > 0 else "slow_down",
                    value=new_spd,
                    cost=abs(ds) / 20.0 + 0.5,
                ))

        return cands

    def evaluate(self, own: Aircraft, other: Aircraft, res: Resolution) -> float:
        """
        Apply the resolution, run a short what-if, return a cost.
        Cost = base_cost + residual_conflict_penalty.
        """
        test = own.copy()
        if res.manoeuvre in ("climb", "descend"):
            test.vertical_rate_fpm = res.value
        elif res.manoeuvre in ("left", "right"):
            test.heading = res.value
        elif res.manoeuvre in ("speed_up", "slow_down"):
            test.speed_kts = res.value

        still_conflict = self._simulate_pair(test, other, duration=240.0)
        if still_conflict:
            return res.cost + 50.0   # heavy penalty
        return res.cost

    def resolve(self, conflict: Conflict, aircraft: List[Aircraft]) -> Optional[Resolution]:
        """
        Pick the best resolution for the first aircraft in the pair.
        (Real systems often resolve both or choose the one with more options.)
        """
        ac_map = {a.callsign: a for a in aircraft}
        if conflict.ac1 not in ac_map or conflict.ac2 not in ac_map:
            return None

        own = ac_map[conflict.ac1]
        other = ac_map[conflict.ac2]

        candidates = self.generate_candidates(own, other)
        if not candidates:
            return None

        best = None
        best_cost = 1e9
        for c in candidates:
            cost = self.evaluate(own, other, c)
            if cost < best_cost:
                best_cost = cost
                best = c
                best.cost = cost
                best.resolved = cost < 40.0   # heuristic threshold

        return best

    def apply(self, aircraft: List[Aircraft], resolution: Resolution):
        """Actually command the aircraft."""
        for ac in aircraft:
            if ac.callsign == resolution.callsign:
                if resolution.manoeuvre in ("climb", "descend"):
                    ac.apply_control(new_vs_fpm=resolution.value)
                elif resolution.manoeuvre in ("left", "right"):
                    ac.apply_control(new_heading=resolution.value)
                elif resolution.manoeuvre in ("speed_up", "slow_down"):
                    ac.apply_control(new_speed_kts=resolution.value)
                ac.resolved = True
                ac.resolution_cmd = f"{resolution.manoeuvre} {resolution.value:.0f}"
                break
