"""
A couple of smoke tests so you know the core still works after changes.
Run with: python -m pytest tests/ -q
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aircraft import Aircraft
from src.weather import WeatherField
from src.conflict_detection import ConflictDetector
from src.simulation import ATMSimulation
from src.utils import haversine_distance, knots_to_ms


def test_aircraft_step_moves():
    ac = Aircraft("TEST1", 40.0, -75.0, 30000, 400, 90)
    start_lon = ac.lon
    ac.step(10.0)  # 10 seconds eastbound
    assert ac.lon > start_lon
    assert ac.alt_ft == 30000


def test_haversine_known_distance():
    # roughly 1 degree of latitude ≈ 111 km
    d = haversine_distance(40.0, -75.0, 41.0, -75.0)
    assert 110000 < d < 112000


def test_conflict_head_on():
    a = Aircraft("A", 40.0, -75.2, 35000, 450, 90)
    b = Aircraft("B", 40.0, -74.8, 35000, 450, 270)
    det = ConflictDetector(lookahead=600)
    c = det.check_pair(a, b)
    assert c is not None
    assert c.t_cpa > 0
    assert c.dist_cpa_nm < 5.0


def test_simulation_runs():
    aircraft = [
        Aircraft("A", 40.1, -75.3, 35000, 440, 90),
        Aircraft("B", 40.1, -74.7, 35000, 440, 270),
    ]
    sim = ATMSimulation(aircraft, duration=60.0, dt=2.0, auto_resolve=False)
    summary = sim.run(verbose=False)
    assert summary["duration"] == 60.0
    assert len(summary["trajectories"]) == 2


def test_weather_sample():
    w = WeatherField(base_wind_speed_kts=20, base_wind_dir_deg=270)
    s = w.sample(40.0, -75.0, 10000)
    assert s.wind_speed_kts > 0
    assert 0 <= s.wind_dir_deg < 360


if __name__ == "__main__":
    test_aircraft_step_moves()
    test_haversine_known_distance()
    test_conflict_head_on()
    test_simulation_runs()
    test_weather_sample()
    print("All basic tests passed.")
