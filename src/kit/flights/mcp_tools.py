"""MCP tool registrations for flight search."""

from __future__ import annotations

from datetime import date

from mcp.server.fastmcp import FastMCP

from kit.config import KitConfig
from kit.flights.core import FlightSearch
from kit.flights.planner import search_flights


def register_flights_tools(mcp: FastMCP, config: KitConfig) -> None:
    """Register flight-search tools on the given FastMCP server."""

    @mcp.tool()
    def kit_flight_search(
        origin: str,
        destination: str,
        date_from: str,
        date_to: str,
        trip_type: str = "one_way",
        nights_min: int | None = None,
        nights_max: int | None = None,
        max_results: int = 20,
    ) -> str:
        """Search Ryanair for cheapest flights in a date window.

        Uses Ryanair's public fare API directly (no third-party service).
        Returns all matching options sorted by price, plus the cheapest pick.

        Args:
            origin: IATA code (e.g. 'BER') or airport name.
            destination: IATA code or airport name.
            date_from: Earliest outbound departure date (YYYY-MM-DD).
            date_to: Latest date to consider (YYYY-MM-DD).
            trip_type: 'one_way' or 'round_trip'.
            nights_min: Round-trip only — min nights at destination.
            nights_max: Round-trip only — max nights at destination.
            max_results: Maximum options to return (default 20).
        """
        query = FlightSearch(
            origin=origin,
            destination=destination,
            date_from=date.fromisoformat(date_from),
            date_to=date.fromisoformat(date_to),
            trip_type="round_trip" if trip_type == "round_trip" else "one_way",
            nights_min=nights_min,
            nights_max=nights_max,
            max_results=max_results,
        )
        result = search_flights(query)
        return result.model_dump_json(indent=2)
