#!/usr/bin/env python3
"""
Air Traffic Management Simulation — entry point.

Run a demo scenario that shows:
  - 4D trajectories under wind
  - conflict detection
  - automatic resolution
  - a couple of plots at the end

Usage:
    python main.py
    python main.py --no-resolve      # just detect, don't fix
    python main.py --duration 900
"""

import argparse
import sys
from pathlib import Path

# make sure we can import from src/
sys.path.insert(0, str(Path(__file__).parent))

from src.aircraft import Aircraft
from src.weather import WeatherField
from src.simulation import ATMSimulation
from src.utils import meters_to_feet

import matplotlib.pyplot as plt
import numpy as np


def build_demo_scenario() -> list[Aircraft]:
    """
    Four aircraft in a busy-ish terminal area.
    Two pairs are set up to conflict if nothing is done.
    """
    # reference roughly around a fictional airport (say near 40N 75W)
    aircraft = [
        # Flight 1 — eastbound at FL350
        Aircraft(
            callsign="AAL123",
            lat=40.10, lon=-75.40,
            alt_ft=35000,
            speed_kts=450,
            heading=90,
            vertical_rate_fpm=0,
            aircraft_type="B738",
        ),
        # Flight 2 — westbound, same level → head-on conflict
        Aircraft(
            callsign="UAL456",
            lat=40.12, lon=-74.60,
            alt_ft=35000,
            speed_kts=460,
            heading=270,
            vertical_rate_fpm=0,
            aircraft_type="A320",
        ),
        # Flight 3 — climbing through FL280, will cross path of Flight 4
        Aircraft(
            callsign="DAL789",
            lat=39.85, lon=-75.10,
            alt_ft=26000,
            speed_kts=380,
            heading=45,
            vertical_rate_fpm=1800,
            aircraft_type="B737",
        ),
        # Flight 4 — descending, crossing path
        Aircraft(
            callsign="JBU321",
            lat=40.30, lon=-74.90,
            alt_ft=32000,
            speed_kts=400,
            heading=200,
            vertical_rate_fpm=-1200,
            aircraft_type="A321",
        ),
    ]
    return aircraft


def plot_results(summary: dict, save: bool = True):
    """Two plots: horizontal tracks and altitude vs time."""
    trajs = summary["trajectories"]
    colors = plt.cm.tab10(np.linspace(0, 1, len(trajs)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # --- horizontal ---
    for (callsign, traj), color in zip(trajs.items(), colors):
        lats, lons = traj.horizontal_path()
        ax1.plot(lons, lats, "-o", color=color, markersize=3, label=callsign, linewidth=1.5)
        # start / end markers
        if len(lats):
            ax1.plot(lons[0], lats[0], "o", color=color, markersize=8)
            ax1.plot(lons[-1], lats[-1], "s", color=color, markersize=7)

    ax1.set_xlabel("Longitude")
    ax1.set_ylabel("Latitude")
    ax1.set_title("Horizontal Tracks")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect("equal", adjustable="datalim")

    # --- vertical ---
    for (callsign, traj), color in zip(trajs.items(), colors):
        ts, alts = traj.altitude_profile()
        ax2.plot(ts / 60.0, alts, color=color, label=callsign, linewidth=1.8)

    ax2.set_xlabel("Time (min)")
    ax2.set_ylabel("Altitude (ft)")
    ax2.set_title("Altitude Profiles")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    fig.suptitle("ATM Simulation — 4D Trajectories", fontsize=13)
    plt.tight_layout()

    if save:
        out = Path("results")
        out.mkdir(exist_ok=True)
        fig.savefig(out / "trajectories.png", dpi=140)
        print(f"\nPlot saved to {out / 'trajectories.png'}")

    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Air Traffic Management Simulation")
    parser.add_argument("--duration", type=float, default=480.0,
                        help="Simulation duration in seconds (default 480)")
    parser.add_argument("--dt", type=float, default=2.0, help="Time step (s)")
    parser.add_argument("--no-resolve", action="store_true",
                        help="Disable automatic conflict resolution")
    parser.add_argument("--wind", type=float, default=30.0,
                        help="Background wind speed in knots")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("  Air Traffic Management Simulation")
    print("  4D trajectories · Conflict detection · Weather")
    print("=" * 60)

    aircraft = build_demo_scenario()
    weather = WeatherField(
        base_wind_speed_kts=args.wind,
        base_wind_dir_deg=250.0,
        turbulence_intensity=0.12,
    )

    print(f"\nScenario: {len(aircraft)} aircraft, wind {args.wind:.0f} kt from 250\u00b0")
    print("Aircraft:")
    for ac in aircraft:
        print(f"  {ac}")

    sim = ATMSimulation(
        aircraft=aircraft,
        weather=weather,
        dt=args.dt,
        duration=args.duration,
        auto_resolve=not args.no_resolve,
    )

    print("\nRunning simulation...")
    summary = sim.run(verbose=True)
    sim.print_summary(summary)

    if not args.no_plot:
        plot_results(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
