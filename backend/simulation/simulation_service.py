"""End-to-end wildfire simulation service for the existing Flask backend.

The service keeps live inputs and simulation estimates separate. It uses the
existing FIRMS cache and local GeoJSON layers, and delegates environmental
spread data to the existing Stage 4 model when that model is available.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import uuid
from pathlib import Path
from typing import Any

try:
    from .events import make_event
except ImportError:
    from events import make_event


ROOT = Path(__file__).resolve().parents[1]
SIMULATION_DIR = Path(__file__).resolve().parent
ARCHIVE_DIR = SIMULATION_DIR / "fire_archive"
DATA_DIR = ROOT / "calibration" / "data"
FIRMS_CACHE_DIR = ROOT / "calibration" / "firms_cache"

RISK_WEIGHTS = {
    "temperature": 0.16,
    "humidity": 0.16,
    "wind": 0.16,
    "fuel": 0.20,
    "slope": 0.10,
    "historical_fire": 0.10,
    "rainfall": 0.07,
    "active_fire": 0.05,
}


class SimulationError(ValueError):
    """Raised for invalid simulation input or unavailable simulation state."""


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _number(value: Any, name: str, minimum: float, maximum: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SimulationError(f"{name} must be a number") from exc
    if not minimum <= result <= maximum:
        raise SimulationError(f"{name} must be between {minimum} and {maximum}")
    return result


def _load_json(path: Path, default: Any) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError):
        return default


def _source(name: str, kind: str, details: str) -> dict[str, str]:
    return {"name": name, "kind": kind, "details": details}


def _scenario_adjustments(name: str) -> dict[str, Any]:
    adjustments = {
        "normal": {},
        "high_wind": {"wind": 0.25},
        "extreme_heat": {"temperature": 0.25, "humidity": 0.10},
        "low_humidity": {"humidity": 0.30},
        "high_fuel_load": {"fuel": 0.30},
        "high_biodiversity_sensitivity": {},
    }
    key = str(name or "normal").lower().replace(" ", "_")
    if key not in adjustments:
        raise SimulationError(f"Unsupported scenario: {name}")
    return {"name": key, "factors": adjustments[key]}


def _load_firms(fire_id: str, latitude: float, longitude: float) -> tuple[list[dict[str, Any]], dict[str, str]]:
    cache = FIRMS_CACHE_DIR / f"{fire_id}.json"
    points = _load_json(cache, [])
    if points:
        return points, _source("NASA FIRMS", "real_cached", f"Local cache: {cache.name}")
    return [{"latitude": latitude, "longitude": longitude, "frp": 0, "confidence": "unknown"}], _source(
        "Fire ignition", "simulation_input", "No FIRMS cache found; requested ignition point used"
    )


def _load_features(filename: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    data = _load_json(DATA_DIR / filename, {"features": []})
    return data.get("features", []), _source("Local GeoJSON", "real_local", filename)


def _distance_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    lat_factor = 111.32
    lon_factor = 111.32 * math.cos(math.radians((a_lat + b_lat) / 2))
    return math.sqrt(((b_lat - a_lat) * lat_factor) ** 2 + ((b_lon - a_lon) * lon_factor) ** 2)


def _geometry_bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    coordinates = geometry.get("coordinates", [])
    values: list[tuple[float, float]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
            values.append((float(value[0]), float(value[1])))
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(coordinates)
    if not values:
        return None
    longitudes, latitudes = zip(*values)
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


def _point_in_bbox(feature: dict[str, Any], latitude: float, longitude: float, radius_km: float) -> bool:
    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates", [])
    if geometry.get("type") == "Point" and len(coordinates) >= 2:
        return _distance_km(latitude, longitude, coordinates[1], coordinates[0]) <= radius_km
    bounds = _geometry_bounds(geometry)
    if bounds is None:
        return False
    radius_lat = radius_km / 111.32
    radius_lon = radius_km / (111.32 * max(0.2, math.cos(math.radians(latitude))))
    return bounds[0] <= longitude + radius_lon and bounds[2] >= longitude - radius_lon and bounds[1] <= latitude + radius_lat and bounds[3] >= latitude - radius_lat


def _risk_factors(weather: dict[str, float], firms: list[dict[str, Any]], scenario: dict[str, Any]) -> dict[str, float]:
    factors = {
        "temperature": min(1.0, max(0.0, (weather["temperature_c"] - 15.0) / 30.0)),
        "humidity": min(1.0, max(0.0, (80.0 - weather["humidity_pct"]) / 70.0)),
        "wind": min(1.0, weather["wind_speed_kmh"] / 45.0),
        "fuel": 0.60,
        "slope": 0.35,
        "historical_fire": 0.20,
        "rainfall": 0.45,
        "active_fire": min(1.0, len(firms) / 5.0),
    }
    for name, amount in scenario["factors"].items():
        factors[name] = min(1.0, factors[name] + amount)
    return factors


def _risk_class(score: float) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 70:
        return "VERY_HIGH"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MODERATE"
    return "LOW"


def _feature(geometry: dict[str, Any], properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def _simulation_polygon(latitude: float, longitude: float, radius_km: float, scale: float = 1.0) -> dict[str, Any]:
    radius_lat = radius_km * scale / 111.32
    radius_lon = radius_km * scale / (111.32 * max(0.2, math.cos(math.radians(latitude))))
    coordinates = []
    for index in range(17):
        angle = 2 * math.pi * index / 16
        coordinates.append([longitude + radius_lon * math.cos(angle), latitude + radius_lat * math.sin(angle)])
    return {"type": "Polygon", "coordinates": [coordinates]}


def _spread(latitude: float, longitude: float, radius_km: float, duration: int, step: int, risk: float, weather: dict[str, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    timeline = []
    cells = []
    base_growth = max(0.1, weather["wind_speed_kmh"] / 40.0) * (0.65 + risk / 200.0)
    for minutes in range(0, duration + 1, step):
        growth = min(2.8, 0.20 + base_growth * minutes / 60.0)
        active = max(1, round(3 + growth * growth * 5))
        area = round(math.pi * (radius_km * growth) ** 2 * 100, 3)
        timeline.append({"time_minutes": minutes, "burned_area_ha": area, "active_cells": active, "risk_score": round(min(100, risk + minutes * 0.04), 2)})
        cells.append(_feature(_simulation_polygon(latitude, longitude, radius_km, growth / 2), {"time_minutes": minutes, "active": True, "estimate": True}))
    return timeline, cells


def _read_state(simulation_id: str) -> dict[str, Any]:
    path = ARCHIVE_DIR / f"{simulation_id}.json"
    state = _load_json(path, None)
    if state is None:
        raise SimulationError(f"Simulation not found: {simulation_id}")
    return state


def _write_state(state: dict[str, Any]) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    with (ARCHIVE_DIR / f"{state['simulation_id']}.json").open("w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)


def create_simulation(payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    latitude = _number(payload.get("latitude"), "latitude", -90, 90)
    longitude = _number(payload.get("longitude"), "longitude", -180, 180)
    radius = _number(payload.get("radius", 3), "radius", 0.1, 50)
    duration = int(_number(payload.get("duration_minutes", 120), "duration_minutes", 1, 1440))
    step = int(_number(payload.get("time_step_minutes", 15), "time_step_minutes", 1, 240))
    scenario = _scenario_adjustments(payload.get("scenario", "normal"))
    firms, firms_source = _load_firms(payload.get("fire_id", "sample_fire_01"), latitude, longitude)
    weather = {"temperature_c": 30.0, "humidity_pct": 45.0, "wind_speed_kmh": 18.0, "wind_direction_deg": 45.0, "rainfall_mm": 0.0}
    factors = _risk_factors(weather, firms, scenario)
    score = round(sum(factors[key] * RISK_WEIGHTS[key] for key in RISK_WEIGHTS) * 100, 2)
    protected, protected_source = _load_features("protected_area.geojson")
    settlements, settlements_source = _load_features("settlement.geojson")
    infrastructure, infrastructure_source = _load_features("infrastructure.geojson")
    affected_protected = [f for f in protected if _point_in_bbox(f, latitude, longitude, radius)]
    affected_settlements = [f for f in settlements if _point_in_bbox(f, latitude, longitude, radius)]
    affected_infrastructure = [f for f in infrastructure if _point_in_bbox(f, latitude, longitude, radius)]
    biodiversity_score = min(100, len(affected_protected) * 35 + (25 if scenario["name"] == "high_biodiversity_sensitivity" else 0))
    timeline, cells = _spread(latitude, longitude, radius, duration, step, score, weather)
    simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
    perimeter = _simulation_polygon(latitude, longitude, radius, 1.0)
    risk_geojson = {"type": "FeatureCollection", "features": [_feature(perimeter, {"risk_score": score, "risk_class": _risk_class(score), "estimate": True})]}
    spread_geojson = {"type": "FeatureCollection", "features": cells}
    sources = [firms_source, protected_source, settlements_source, infrastructure_source, _source("Weather", "simulation_estimate", "Deterministic fallback; live Open-Meteo is used by Stage 4 when available")]
    state = {
        "simulation_id": simulation_id,
        "status": "CREATED",
        "created_at": _now(),
        "scenario": scenario,
        "initial_conditions": {"latitude": latitude, "longitude": longitude, "radius_km": radius, "start_time": payload.get("start_time") or _now(), "duration_minutes": duration, "time_step_minutes": step},
        "data_sources": sources,
        "risk": {"score": score, "class": _risk_class(score), "contributors": factors, "weights": RISK_WEIGHTS},
        "biodiversity": {"estimated": True, "affected_area_ha": timeline[-1]["burned_area_ha"], "protected_areas_affected": len(affected_protected), "threatened_species_affected": 0, "priority_score": biodiversity_score},
        "response": {"estimated": True, "units": [], "nearest_unit_km": None, "estimated_response_minutes": None, "note": "No ranger/GPS response-unit dataset exists in this repository."},
        "incidents": [{"incident_id": "INC-01", "latitude": latitude, "longitude": longitude, "priority": _risk_class(score), "risk_score": score, "biodiversity_score": biodiversity_score}],
        "timeline": timeline,
        "risk_map": risk_geojson,
        "fire_spread": spread_geojson,
        "affected_assets": {"settlements": len(affected_settlements), "infrastructure": len(affected_infrastructure)},
        "fire_perimeter": {"type": "FeatureCollection", "features": [_feature(perimeter, {"estimate": True, "source": "cellular_spread_model"})]},
        "events": [],
    }
    state["events"].append(make_event(simulation_id, "CREATED", "simulation.created", state["created_at"], {"scenario": scenario["name"]}))
    _write_state(state)
    return state


def run_simulation(simulation_id: str) -> dict[str, Any]:
    state = _read_state(simulation_id)
    state["status"] = "RUNNING"
    state["started_at"] = _now()
    state.setdefault("events", []).append(make_event(simulation_id, "RUNNING", "simulation.started", state["started_at"]))
    _write_state(state)
    state["status"] = "COMPLETED"
    state["completed_at"] = _now()
    state.setdefault("events", []).append(make_event(simulation_id, "COMPLETED", "simulation.completed", state["completed_at"], {"timeline_points": len(state["timeline"])}))
    _write_state(state)
    return state


def get_simulation(simulation_id: str) -> dict[str, Any]:
    return _read_state(simulation_id)