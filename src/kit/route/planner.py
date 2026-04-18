"""High-level route planning API."""

from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, timedelta, timezone
from typing import Any, overload

from kit.config import KitConfig, load_config
from kit.errors import ConfigError, KitError
from kit.route.core import RouteRequest, RouteResult, TransportMode
from kit.route.google_maps import GoogleMapsRouter
from kit.utils.geo import parse_location

_TZ = timezone(timedelta(hours=1))


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
    departure: datetime | None = None,
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
        leg_departure = departure if i == 0 else None
        req = RouteRequest(
            origin=origin, destination=dest, mode=mode, departure=leg_departure,
        )
        results.append(router.plan(req))

    return results


def plan_day(
    tasks: list[str],
    schedule_date: date_cls | None = None,
    start_hour: int = 9,
    end_hour: int = 18,
    config: KitConfig | None = None,
) -> dict[str, Any]:
    """Build a sequential day schedule from tasks ('Name @ Location' format).

    Inserts travel legs (+5min buffer) between consecutively located tasks via
    ``plan_route``. Falls back to a 15-min buffer on routing errors.
    """
    schedule_date = schedule_date or datetime.now(tz=_TZ).date()
    parsed = []
    for task in tasks:
        if " @ " in task:
            name, loc = task.rsplit(" @ ", 1)
            parsed.append({"name": name.strip(), "location": loc.strip()})
        else:
            parsed.append({"name": task.strip(), "location": None})

    current = datetime(
        schedule_date.year, schedule_date.month, schedule_date.day,
        start_hour, 0, tzinfo=_TZ,
    )
    schedule: list[dict[str, Any]] = []
    prev_loc: str | None = None

    for t in parsed:
        travel = None
        if prev_loc and t["location"]:
            try:
                route = plan_route(prev_loc, t["location"], config=config)
                mins = (route.duration_seconds + 59) // 60
                travel = {
                    "from": prev_loc, "to": t["location"],
                    "duration_minutes": mins,
                    "duration_human": route.duration_human,
                    "deep_links": route.deep_links.model_dump(),
                }
                current += timedelta(minutes=mins + 5)
            except KitError:
                current += timedelta(minutes=15)

        entry: dict[str, Any] = {
            "time": current.strftime("%H:%M"),
            "task": t["name"], "location": t["location"],
        }
        if travel:
            entry["travel"] = travel
        schedule.append(entry)
        current += timedelta(minutes=60)
        if t["location"]:
            prev_loc = t["location"]

    return {
        "date": str(schedule_date),
        "schedule": schedule,
        "start": f"{start_hour:02d}:00",
        "end": f"{end_hour:02d}:00",
    }
