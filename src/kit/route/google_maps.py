"""Google Maps Directions + Geocoding client."""

from __future__ import annotations

from datetime import datetime, timezone

import googlemaps

from kit.errors import APIError, GeocodingError, RouteNotFoundError
from kit.route.core import DeepLinks, RouteRequest, RouteResult, RouteStep
from kit.route.deep_links import generate_deep_links
from kit.route.deep_links import TransportMode as DLTransportMode


class GoogleMapsRouter:
    """Wraps the googlemaps library for directions and geocoding."""

    def __init__(self, api_key: str) -> None:
        self._client = googlemaps.Client(key=api_key)

    # --- Directions ---

    def plan(self, request: RouteRequest) -> RouteResult:
        """Plan a route using Google Maps Directions API.

        Args:
            request: A RouteRequest with origin, destination, mode, etc.

        Returns:
            RouteResult with duration, steps, and deep links.

        Raises:
            RouteNotFoundError: No route found for the given parameters.
            APIError: Network or authentication failure.
        """
        kwargs: dict = {
            "origin": request.origin,
            "destination": request.destination,
            "mode": request.mode.value,
            "alternatives": request.alternatives > 1,
        }
        if request.departure:
            kwargs["departure_time"] = request.departure
        if request.arrival:
            kwargs["arrival_time"] = request.arrival

        try:
            results = self._client.directions(**kwargs)
        except Exception as e:
            raise APIError(f"Google Maps API error: {e}") from e

        if not results:
            raise RouteNotFoundError(
                f"No route found from '{request.origin}' to '{request.destination}' "
                f"via {request.mode.value}"
            )

        route = results[0]
        leg = route["legs"][0]

        steps = [_parse_step(s) for s in leg.get("steps", [])]

        dep_time = leg.get("departure_time", {}).get("value")
        arr_time = leg.get("arrival_time", {}).get("value")
        departure = (
            datetime.fromtimestamp(dep_time, tz=timezone.utc)
            if dep_time
            else request.departure or datetime.now(tz=timezone.utc)
        )
        arrival_dt = (
            datetime.fromtimestamp(arr_time, tz=timezone.utc)
            if arr_time
            else departure
        )

        # generate_deep_links uses its own TransportMode enum — convert by value
        dl_mode = DLTransportMode(request.mode.value)
        dl = generate_deep_links(
            request.origin,
            request.destination,
            dl_mode,
            departure=departure,
        )
        # Convert frozen dataclass → Pydantic DeepLinks expected by RouteResult
        deep_links = DeepLinks(
            google_maps=dl.google_maps,
            apple_maps=dl.apple_maps,
            db_navigator=dl.db_navigator,
            bvg=dl.bvg,
        )

        return RouteResult(
            origin=leg.get("start_address", request.origin),
            destination=leg.get("end_address", request.destination),
            mode=request.mode,
            duration_seconds=leg["duration"]["value"],
            departure=departure,
            arrival=arrival_dt,
            steps=steps,
            deep_links=deep_links,
        )

    # --- Geocoding ---

    def geocode(self, address: str) -> tuple[float, float]:
        """Geocode an address to (lat, lng).

        Args:
            address: Free-form address string.

        Returns:
            Tuple of (latitude, longitude).

        Raises:
            GeocodingError: Address could not be resolved.
            APIError: Network or authentication failure.
        """
        try:
            results = self._client.geocode(address)
        except Exception as e:
            raise APIError(f"Google Maps geocoding error: {e}") from e

        if not results:
            raise GeocodingError(f"Could not geocode address: '{address}'")

        location = results[0]["geometry"]["location"]
        return location["lat"], location["lng"]


def _parse_step(step: dict) -> RouteStep:
    """Parse a single step from the Directions API response."""
    transit = step.get("transit_details", {})
    return RouteStep(
        instruction=step.get("html_instructions", ""),
        mode=step.get("travel_mode", "").lower(),
        distance_meters=step.get("distance", {}).get("value", 0),
        duration_seconds=step.get("duration", {}).get("value", 0),
        transit_line=transit.get("line", {}).get("short_name"),
        transit_stops=transit.get("num_stops"),
    )
