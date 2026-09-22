from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    event_id: int
    simulation_day: float
    timestamp: datetime
    event_type: str
    entity_type: str
    entity_id: str
    location_id: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


class EventLog:
    def __init__(self) -> None:
        self._events: list[SimulationEvent] = []

    def append(self, event: SimulationEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> tuple[SimulationEvent, ...]:
        return tuple(self._events)

    def digest(self) -> str:
        canonical = json.dumps(
            [event.as_dict() for event in self._events],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
