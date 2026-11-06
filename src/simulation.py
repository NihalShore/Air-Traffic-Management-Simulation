"""
Main simulation loop.
Keeps the clock, steps every aircraft, runs detection & resolution,
and collects results for plotting / logging.
"""

from typing import List, Dict, Optional, Callable
import time
import numpy as np

from .aircraft import Aircraft
from .weather import WeatherField
from .conflict_detection import ConflictDetector, Conflict
from .conflict_resolution import ConflictResolver, Resolution
from .trajectory import Trajectory4D


class ATMSimulation:
    def __init__(self,
                 aircraft: List[Aircraft],
                 weather: Optional[WeatherField] = None,
                 dt: float = 2.0,
                 duration: float = 600.0,
                 auto_resolve: bool = True):
        self.aircraft = aircraft
        self.weather = weather or WeatherField()
        self.dt = dt
        self.duration = duration
        self.auto_resolve = auto_resolve

        self.detector = ConflictDetector()
        self.resolver = ConflictResolver(self.detector)

        self.t = 0.0
        self.conflicts_log: List[Conflict] = []
        self.resolutions_log: List[Resolution] = []
        self.running = False

        # optional callback after each step (for live visualisation etc.)
        self.on_step: Optional[Callable] = None

    def reset(self):
        self.t = 0.0
        self.conflicts_log.clear()
        self.resolutions_log.clear()
        for ac in self.aircraft:
            ac.history.clear()
            ac.resolved = False
            ac.resolution_cmd = None
            ac.record(0.0)

    def step(self):
        """One simulation step."""
        # 1. weather + kinematics
        for ac in self.aircraft:
            wn, we = self.weather.wind_at_aircraft(ac, self.t)
            ac.step(self.dt, wind_n=wn, wind_e=we)
            ac.record(self.t + self.dt)

        self.t += self.dt

        # 2. detect
        conflicts = self.detector.detect(self.aircraft)
        for c in conflicts:
            # only log new ones (simple check by pair + rough time)
            already = any(
                (c.ac1 == old.ac1 and c.ac2 == old.ac2 and abs(c.t_cpa - old.t_cpa) < 30)
                for old in self.conflicts_log
            )
            if not already:
                self.conflicts_log.append(c)

        # 3. resolve (only the most urgent one each step to keep it calm)
        if self.auto_resolve and conflicts:
            most_urgent = conflicts[0]
            # don't re-resolve the same aircraft every single step
            ac1 = next(a for a in self.aircraft if a.callsign == most_urgent.ac1)
            if not ac1.resolved:
                res = self.resolver.resolve(most_urgent, self.aircraft)
                if res and res.resolved:
                    self.resolver.apply(self.aircraft, res)
                    self.resolutions_log.append(res)

        if self.on_step:
            self.on_step(self)

    def run(self, verbose: bool = True) -> Dict:
        """Run the whole scenario."""
        self.reset()
        self.running = True
        start_wall = time.time()

        n_steps = int(self.duration / self.dt)
        for i in range(n_steps):
            self.step()
            if verbose and (i + 1) % 50 == 0:
                print(f"  t = {self.t:6.0f}s  |  active aircraft: {len(self.aircraft)}  |  "
                      f"conflicts so far: {len(self.conflicts_log)}")

        self.running = False
        wall = time.time() - start_wall

        # build trajectories
        trajectories = {}
        for ac in self.aircraft:
            traj = Trajectory4D(ac.callsign)
            traj.from_aircraft_history(ac)
            trajectories[ac.callsign] = traj

        summary = {
            "duration": self.t,
            "wall_time": wall,
            "n_aircraft": len(self.aircraft),
            "n_conflicts": len(self.conflicts_log),
            "n_resolutions": len(self.resolutions_log),
            "conflicts": self.conflicts_log,
            "resolutions": self.resolutions_log,
            "trajectories": trajectories,
        }
        return summary

    def print_summary(self, summary: Dict):
        print("\n" + "=" * 60)
        print("SIMULATION SUMMARY")
        print("=" * 60)
        print(f"Simulated time     : {summary['duration']:.0f} s")
        print(f"Wall-clock time    : {summary['wall_time']:.2f} s")
        print(f"Aircraft           : {summary['n_aircraft']}")
        print(f"Conflicts detected : {summary['n_conflicts']}")
        print(f"Resolutions issued : {summary['n_resolutions']}")

        if summary["conflicts"]:
            print("\nConflicts:")
            for c in summary["conflicts"][:10]:
                print(f"  • {c}")

        if summary["resolutions"]:
            print("\nResolutions applied:")
            for r in summary["resolutions"]:
                print(f"  • {r}")

        print("=" * 60)
