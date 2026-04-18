"""Deep link generators for navigation apps.

Generates URL strings for Google Maps, DB Navigator, Apple Maps, and BVG Fahrinfo.
This module is self-contained and does not depend on route core models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from urllib.parse import urlencode


class TransportMode(str, Enum):
    """Transport modes supported by deep link generators."""

    TRANSIT = "transit"
    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"


@dataclass(frozen=True)
class DeepLinks:
    """Collection of deep links for navigation apps."""

    google_maps: str
    apple_maps: str
    db_navigator: str | None = None
    bvg: str | None = None


_MODE_MAP_GMAPS = {
    TransportMode.TRANSIT: "transit",
    TransportMode.WALKING: "walking",
    TransportMode.BICYCLING: "bicycling",
    TransportMode.DRIVING: "driving",
}

_MODE_MAP_APPLE = {
    TransportMode.TRANSIT: "r",
    TransportMode.WALKING: "w",
    TransportMode.DRIVING: "d",
    TransportMode.BICYCLING: "w",  # Apple Maps has no bike mode
}


def generate_deep_links(
    origin: str,
    destination: str,
    mode: TransportMode,
    departure: datetime | None = None,
) -> DeepLinks:
    """Generate deep links for multiple navigation apps.

    Args:
        origin: Start address or place name.
        destination: End address or place name.
        mode: Transport mode (transit, driving, walking, bicycling).
        departure: Optional departure time (used by DB Navigator).

    Returns:
        DeepLinks with URLs for each supported app.
    """
    google_maps = _google_maps_link(origin, destination, mode)
    apple_maps = _apple_maps_link(origin, destination, mode)
    db_navigator = (
        _db_navigator_link(origin, destination, departure)
        if mode == TransportMode.TRANSIT
        else None
    )
    bvg = _bvg_link(origin, destination) if mode == TransportMode.TRANSIT else None

    return DeepLinks(
        google_maps=google_maps,
        db_navigator=db_navigator,
        apple_maps=apple_maps,
        bvg=bvg,
    )


def _google_maps_link(origin: str, destination: str, mode: TransportMode) -> str:
    params = {
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": _MODE_MAP_GMAPS[mode],
    }
    return f"https://www.google.com/maps/dir/?{urlencode(params)}"


def _apple_maps_link(origin: str, destination: str, mode: TransportMode) -> str:
    params = {
        "saddr": origin,
        "daddr": destination,
        "dirflg": _MODE_MAP_APPLE[mode],
    }
    return f"https://maps.apple.com/?{urlencode(params)}"


def _db_navigator_link(
    origin: str,
    destination: str,
    departure: datetime | None = None,
) -> str:
    params: dict[str, str] = {"S": origin, "Z": destination}
    if departure:
        # Convert tz-aware datetimes to system local time so date/time params
        # reflect the user's wall clock (naive datetimes pass through unchanged).
        local_dep = (
            departure.astimezone() if departure.tzinfo is not None else departure
        )
        params["date"] = local_dep.strftime("%d.%m.%Y")
        params["time"] = local_dep.strftime("%H:%M")
    return f"https://reiseauskunft.bahn.de/bin/query.exe/dn?{urlencode(params)}"


def _bvg_link(origin: str, destination: str) -> str:
    params = {"from": origin, "to": destination}
    return f"https://fahrinfo.bvg.de/Fahrinfo/bin/query.bin/dn?{urlencode(params)}"
