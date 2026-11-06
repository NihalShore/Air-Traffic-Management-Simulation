"""Scenario loading and validation for the command-line simulator."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from .aircraft import Aircraft
from .weather import WeatherField


@dataclass
class Scenario:
    name: str
    description: str
    aircraft: list[Aircraft]
    weather: WeatherField
    duration_sec: float
    dt_sec: float
    horizontal_sep_nm: float
    vertical_sep_ft: float
    lookahead_sec: float


def _number(value: Any, field_name: str, *, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field_name}' must be a number") from exc
    if not math.isfinite(number):
        raise ValueError(f"'{field_name}' must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"'{field_name}' must be at least {minimum:g}")
    return number


def load_scenario(path: str | Path) -> Scenario:
    """Read a scenario JSON file and turn it into simulation objects."""
    scenario_path = Path(path)
    try:
        with scenario_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {scenario_path} at line {exc.lineno}, column {exc.colno}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("The scenario file must contain a JSON object")

    aircraft_data = data.get("aircraft")
    if not isinstance(aircraft_data, list) or not aircraft_data:
        raise ValueError("'aircraft' must be a non-empty list")

    aircraft: list[Aircraft] = []
    for index, item in enumerate(aircraft_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Aircraft entry {index} must be a JSON object")
        try:
            aircraft.append(Aircraft(
                callsign=str(item["callsign"]),
                lat=_number(item["lat"], f"aircraft[{index}].lat"),
                lon=_number(item["lon"], f"aircraft[{index}].lon"),
                alt_ft=_number(item["alt_ft"], f"aircraft[{index}].alt_ft"),
                speed_kts=_number(item["speed_kts"], f"aircraft[{index}].speed_kts"),
                heading=_number(item["heading"], f"aircraft[{index}].heading"),
                vertical_rate_fpm=_number(
                    item.get("vertical_rate_fpm", 0.0),
                    f"aircraft[{index}].vertical_rate_fpm",
                ),
                aircraft_type=str(item.get("type", item.get("aircraft_type", "A320"))),
            ))
        except KeyError as exc:
            raise ValueError(
                f"Aircraft entry {index} is missing required field '{exc.args[0]}'"
            ) from exc

    callsigns = [item.callsign for item in aircraft]
    if len(callsigns) != len(set(callsigns)):
        raise ValueError("Aircraft callsigns must be unique")

    weather_data = data.get("weather", {})
    if not isinstance(weather_data, dict):
        raise ValueError("'weather' must be a JSON object")
    weather = WeatherField(
        base_wind_speed_kts=_number(
            weather_data.get("wind_speed_kts", 25.0), "weather.wind_speed_kts", minimum=0
        ),
        base_wind_dir_deg=_number(
            weather_data.get("wind_dir_deg", 270.0), "weather.wind_dir_deg"
        ),
        turbulence_intensity=_number(
            weather_data.get("turbulence", 0.15), "weather.turbulence", minimum=0
        ),
        seed=int(weather_data.get("seed", 42)),
    )
    separation = data.get("separation", {})
    if not isinstance(separation, dict):
        raise ValueError("'separation' must be a JSON object")

    return Scenario(
        name=str(data.get("name", scenario_path.stem)),
        description=str(data.get("description", "")),
        aircraft=aircraft,
        weather=weather,
        duration_sec=_number(data.get("duration_sec", 600.0), "duration_sec", minimum=0.001),
        dt_sec=_number(data.get("dt_sec", 2.0), "dt_sec", minimum=0.001),
        horizontal_sep_nm=_number(
            separation.get("horizontal_nm", 5.0), "separation.horizontal_nm", minimum=0.001
        ),
        vertical_sep_ft=_number(
            separation.get("vertical_ft", 1000.0), "separation.vertical_ft", minimum=0.001
        ),
        lookahead_sec=_number(
            separation.get("lookahead_sec", 300.0), "separation.lookahead_sec", minimum=0
        ),
    )
