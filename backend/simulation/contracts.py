"""Stable JSON contract definitions for frontend integration.

These dataclasses intentionally contain only standard-library types so the
contract can be imported by tooling without requiring Flask, Earth Engine, or
the geospatial stack.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SIMULATION_STATUSES = ("CREATED", "RUNNING", "COMPLETED", "FAILED")
RISK_CLASSES = ("LOW", "MODERATE", "HIGH", "VERY_HIGH", "CRITICAL")
SCENARIOS = (
    "normal",
    "high_wind",
    "extreme_heat",
    "low_humidity",
    "high_fuel_load",
    "high_biodiversity_sensitivity",
)


@dataclass
class SimulationStartRequest:
    latitude: float
    longitude: float
    radius: float = 3.0
    start_time: str | None = None
    duration_minutes: int = 120
    time_step_minutes: int = 15
    scenario: str = "normal"
    fire_id: str = "sample_fire_01"


@dataclass
class SimulationEvent:
    event: str
    simulation_id: str
    status: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ErrorResponse:
    error: str
    code: str
    request_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)