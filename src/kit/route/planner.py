"""High-level route planning API."""

from __future__ import annotations

from typing import overload

from kit.config import KitConfig, load_config
from kit.errors import ConfigError
from kit.route.core import RouteRequest, RouteResult, TransportMode
from kit.route.google_maps import GoogleMapsRouter
from kit.utils.geo import parse_location


def _get_router(config: KitConfig | None = None) -> GoogleMapsRouter:
    config = config or load_config()
    if not config.google_maps_api_key:
        raise ConfigError("Google Maps API key not configured. Run: kit setup")
    return GoogleMapsRouter(api_key=config.google_maps_api_key)


@overload
def plan_route(origin: str, destination: str, /, **kwargs) -> RouteResult: ...


@overload
def plan_route(request: RouteRequest, /) -> RouteResult: ...


def plan_route(origin_or_request, destination=None, /, **kwargs) -> RouteResult:
    """Plan a single route between two locations.

    Can be called two ways:
        plan_route("A", "B")                    — string origin/destination
        plan_route("A", "B", mode=DRIVING)      — with extra options
        plan_route(RouteRequest(...))            — pre-built request object

    Args:
        origin_or_request: Either an origin string or a RouteRequest.
        destination: Destination string (required when origin is a string).
        **kwargs: Extra fields for RouteRequest (mode, departure, arrival).

    Returns:
        RouteResult with duration, steps, and deep links.
    """
    config = kwargs.pop("config", None) or load_config()
    router = _get_router(config)

    if isinstance(origin_or_request, RouteRequest):
        request = origin_or_request
    else:
        origin_loc = parse_location(origin_or_request).resolve(config)
        dest_loc = parse_location(destination).resolve(config)
        request = RouteRequest(origin=origin_loc, destination=dest_loc, **kwargs)

    return router.plan(request)


def plan_multi_route(
    stops: list[str],
    mode: TransportMode = TransportMode.TRANSIT,
    departure: str | None = None,
    config: KitConfig | None = None,
) -> list[RouteResult]:
    """Plan a multi-stop route as sequential legs.

    Plans A->B->C as two legs: A->B, then B->C.

    Args:
        stops: List of location strings (at least 2).
        mode: Transport mode for all legs.
        departure: Optional departure time for the first leg.
        config: Optional KitConfig override.

    Returns:
        List of RouteResult, one per leg.

    Raises:
        ValueError: If fewer than 2 stops are provided.
    """
    if len(stops) < 2:
        raise ValueError("plan_multi_route requires at least 2 stops")

    config = config or load_config()
    router = _get_router(config)
    results: list[RouteResult] = []

    for i in range(len(stops) - 1):
        origin = parse_location(stops[i]).resolve(config)
        dest = parse_location(stops[i + 1]).resolve(config)
        req = RouteRequest(origin=origin, destination=dest, mode=mode)
        results.append(router.plan(req))

    return results
