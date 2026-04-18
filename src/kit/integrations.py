"""
Kit — cross-tool interchange schemas.

Decision: option (d) pure Pydantic interchange, adopted 2026-04-18.
See docs/specs/2026-04-18-cross-tool-integration-hooks.md for full rationale.

Rule
----
Tool modules (route, flights, cal, watch, …) MAY import FROM this module.
They must NOT import each other directly.

Adding a new cross-tool scenario
---------------------------------
1. Define the interchange schema here.
2. Add a conversion method on the source model class
   (e.g. ``FlightOption.as_calendar_event_candidate()``).
3. The consumer reads the standard type — never the source type directly.
   Import ``CalendarEventCandidate`` from ``kit.integrations``, not from
   ``kit.flights``.

Schemas
-------
CalendarEventCandidate  — anything promotable into a calendar event
RouteLeg                — a routable segment between two locations
PriceHit                — a price-alert result (watch → notify / cal)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CalendarEventCandidate(BaseModel):
    """Anything that can be promoted into a Google Calendar event.

    Produced by
    -----------
    ``FlightOption.as_calendar_event_candidate()``
    ``RouteResult.as_calendar_event_candidate()``

    Consumed by
    -----------
    ``cal/mcp_tools.py``, ``cal/commands.py`` — when wiring cross-tool flows.
    """

    title: str
    start: datetime
    end: datetime | None = None
    duration_seconds: int | None = None  # used when end is unknown
    location: str | None = None
    description: str | None = None
    source: str = "unknown"        # "flight" | "route" | "manual" | …
    source_id: str | None = None   # original ID or flight number
    booking_url: str | None = None


class RouteLeg(BaseModel):
    """A routable segment — two locations with optional timing.

    Produced by
    -----------
    ``FlightOption.as_route_leg()``
    ``RouteResult.as_route_leg()``

    Consumed by
    -----------
    Whoever needs travel-buffer computation or leg display without knowing
    the concrete source type.
    """

    origin: str
    destination: str
    departure: datetime | None = None
    duration_seconds: int | None = None
    mode: str | None = None   # "plane" | "transit" | "car" | …


class PriceHit(BaseModel):
    """A price-alert result emitted by the watch tool.

    Produced by
    -----------
    ``watch/monitor`` (not yet built)

    Consumed by
    -----------
    ``notify`` tool, ``cal`` (to suggest booking windows).
    """

    route_key: str        # e.g. "BER-DUB-2026-05-07"
    price: float
    currency: str = "EUR"
    threshold: float
    source: str = "ryanair"
    hit_at: datetime
    booking_url: str | None = None
