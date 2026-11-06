"""
Air Traffic Management Simulation
---------------------------------
4D trajectory modeling, conflict detection & resolution, weather integration.
"""

from .aircraft import Aircraft
from .trajectory import Trajectory4D
from .weather import WeatherField
from .conflict_detection import ConflictDetector
from .conflict_resolution import ConflictResolver
from .simulation import ATMSimulation

__version__ = "1.0.0"
__all__ = [
    "Aircraft",
    "Trajectory4D",
    "WeatherField",
    "ConflictDetector",
    "ConflictResolver",
    "ATMSimulation",
]
