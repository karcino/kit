"""High-level flight search API."""

from __future__ import annotations

from datetime import UTC, datetime

from kit.flights.core import FlightOption, FlightSearch, FlightSearchResult
from kit.flights.ryanair import RyanairFareClient


def search_flights(
    query: FlightSearch,
    client: RyanairFareClient | None = None,
) -> FlightSearchResult:
    """Search Ryanair for cheapest flights matching the query.

    Args:
        query: FlightSearch describing origin, destination, date window, etc.
        client: Optional pre-built client (for tests).

    Returns:
        FlightSearchResult with options sorted by price and the cheapest pick.
    """
    client = client or RyanairFareClient()
    options = client.run_search(query)
    options.sort(key=_sort_key)
    cheapest = min(options, key=lambda o: o.price) if options else None

    return FlightSearchResult(
        query=query,
        options=options[: query.max_results],
        cheapest=cheapest,
        searched_at=datetime.now(tz=UTC),
    )


def _sort_key(option: FlightOption) -> tuple[float, datetime]:
    return (option.price, option.departure)
