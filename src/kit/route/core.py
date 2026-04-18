"""Core data models for route planning."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator


class TransportMode(str, Enum):
    TRANSIT = "transit"
    WALKING = "walking"
    BICYCLING = "bicycling"
    DRIVING = "driving"


class DeepLinks(BaseModel):
    google_maps: str
    db_navigator: str | None = None
    apple_maps: str | None = None
    bvg: str | None = None


class RouteStep(BaseModel):
    instruction: str
    mode: str
    distance_meters: int
    duration_seconds: int
    transit_line: str | None = None
    transit_stops: int | None = None

    @property
    def duration_human(self) -> str:
        return _format_duration(self.duration_seconds)


class RouteRequest(BaseModel):
    origin: str
    destination: str
    mode: TransportMode = TransportMode.TRANSIT
    departure: datetime | None = None
    arrival: datetime | None = None
    alternatives: int = 1

    @model_validator(mode="after")
    def check_times_exclusive(self) -> RouteRequest:
        if self.departure and self.arrival:
            raise ValueError("departure and arrival are mutually exclusive")
        return self


class RouteResult(BaseModel):
    origin: str
    destination: str
    mode: TransportMode
    duration_seconds: int
    departure: datetime
    arrival: datetime
    steps: list[RouteStep]
    deep_links: DeepLinks

    @property
    def duration_human(self) -> str:
        return _format_duration(self.duration_seconds)

    # ── Cross-tool interchange (option d — kit.integrations) ──────────────

    def as_route_leg(self) -> "RouteLeg":
        """Return this result as a RouteLeg interchange shape.

        Consumers (e.g. a day-planner) can work with RouteLeg without
        importing ``kit.route`` directly.
        """
        from kit.integrations import RouteLeg  # lazy — avoids parse-time coupling

        return RouteLeg(
            origin=self.origin,
            destination=self.destination,
            departure=self.departure,
            duration_seconds=self.duration_seconds,
            mode=self.mode.value,
        )


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes}min"
    return f"{minutes} min"
