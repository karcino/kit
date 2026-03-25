"""MCP tool registrations for route planning."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from kit.config import KitConfig
from kit.route.core import TransportMode
from kit.route.planner import plan_route, plan_multi_route
from kit.utils.formatting import format_duration


def register_route_tools(mcp: FastMCP, config: KitConfig) -> None:
    """Register route-planning tools on the given FastMCP server."""

    @mcp.tool()
    def kit_route(
        origin: str,
        destination: str,
        mode: str = "transit",
        departure_time: str | None = None,
        arrival_time: str | None = None,
    ) -> str:
        """Calculate a route between two locations using Google Maps.

        Returns duration, steps, and deep links to navigation apps
        (Google Maps, DB Navigator, Apple Maps).

        Supports addresses, coordinates (lat,lng), and saved locations
        like 'home'.

        Args:
            origin: Start location (address, coordinates, or 'home').
            destination: End location (address, coordinates, or 'home').
            mode: Transport mode — one of 'transit', 'driving', 'walking', 'bicycling'.
            departure_time: Optional departure time (ISO 8601 or natural language).
            arrival_time: Optional desired arrival time (ISO 8601 or natural language).
        """
        result = plan_route(origin, destination, mode=TransportMode(mode), config=config)
        return result.model_dump_json(indent=2)

    @mcp.tool()
    def kit_route_multi(
        stops: list[str],
        mode: str = "transit",
        departure_time: str | None = None,
    ) -> str:
        """Calculate routes between multiple stops in sequence.

        Plans A->B->C as two legs: A->B then B->C.
        Returns total travel time and per-leg details with deep links.

        Args:
            stops: List of location strings (at least 2).
            mode: Transport mode — one of 'transit', 'driving', 'walking', 'bicycling'.
            departure_time: Optional departure time for the first leg.
        """
        results = plan_multi_route(stops, mode=TransportMode(mode), config=config)
        total = sum(r.duration_seconds for r in results)
        output = {
            "total_duration_seconds": total,
            "total_duration_human": format_duration(total),
            "legs": [json.loads(r.model_dump_json()) for r in results],
        }
        return json.dumps(output, indent=2, ensure_ascii=False)
