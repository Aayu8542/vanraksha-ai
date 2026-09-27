"""Archive-backed event delivery for simulation consumers.

The current backend has Flask but no WebSocket dependency. SSE is therefore
the implemented streaming transport; the event envelope is transport-neutral
and can be forwarded through WebSocket later without changing its schema.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

try:
    from .contracts import SimulationEvent
except ImportError:
    from contracts import SimulationEvent


def make_event(simulation_id: str, status: str, event: str, timestamp: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return SimulationEvent(
        event=event,
        simulation_id=simulation_id,
        status=status,
        timestamp=timestamp,
        data=data or {},
    ).as_dict()


def sse_encode(events: list[dict[str, Any]]) -> Iterator[str]:
    for event in events:
        yield f"event: {event['event']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"