"""Ryanair public fare API client.

Uses the same endpoints that ryanair.com itself calls. No authentication,
no subscription, no rate limits we've hit. For one-way queries the API
returns one fare per day for a whole month; we loop per month when the
query spans multiple months and filter to the requested date window.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import httpx

from kit.errors import APIError, FlightSearchError
from kit.flights.core import FlightOption, FlightSearch

RYANAIR_BASE_URL = "https://www.ryanair.com/api/farfnd/v4"
DEFAULT_TIMEOUT = 30.0
# Ryanair 403s requests with no User-Agent. Browser UA avoids that.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.ryanair.com/",
}


class RyanairFareClient:
    """Calls Ryanair's public cheapest-per-day fare endpoints."""

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.timeout = timeout
        self._client = http_client or httpx.Client(timeout=timeout, headers=_HEADERS)

    def run_search(self, query: FlightSearch) -> list[FlightOption]:
        months = _months_spanning(query.date_from, query.date_to)

        if query.trip_type == "one_way":
            outbound = self._fetch_one_way_months(query, months)
            return [o for o in outbound if _in_window(o.departure.date(), query)]

        inbound_months = _months_spanning(
            query.date_from, query.date_to + timedelta(days=query.nights_max or 30)
        )
        outbound = self._fetch_one_way_months(query, months)
        inbound = self._fetch_inbound_months(query, inbound_months)
        return _pair_round_trip(outbound, inbound, query)

    # ---- HTTP layer -------------------------------------------------------

    def _fetch_one_way_months(
        self, query: FlightSearch, months: list[date]
    ) -> list[FlightOption]:
        url = f"{RYANAIR_BASE_URL}/oneWayFares/{query.origin}/{query.destination}/cheapestPerDay"
        return self._fetch_cheapest_per_day(url, query, months, direction="outbound")

    def _fetch_inbound_months(
        self, query: FlightSearch, months: list[date]
    ) -> list[FlightOption]:
        url = (
            f"{RYANAIR_BASE_URL}/roundTripFares/"
            f"{query.origin}/{query.destination}/cheapestPerDay"
        )
        options: list[FlightOption] = []
        for month in months:
            params = {
                "outboundMonthOfDate": month.isoformat(),
                "inboundMonthOfDate": month.isoformat(),
            }
            data = self._get_json(url, params)
            for fare in (data.get("inbound") or {}).get("fares") or []:
                parsed = _parse_fare(
                    fare,
                    origin=query.destination,
                    destination=query.origin,
                )
                if parsed is not None:
                    options.append(parsed)
        return options

    def _fetch_cheapest_per_day(
        self,
        url: str,
        query: FlightSearch,
        months: list[date],
        direction: str,
    ) -> list[FlightOption]:
        options: list[FlightOption] = []
        for month in months:
            params = {"outboundMonthOfDate": month.isoformat()}
            data = self._get_json(url, params)
            for fare in (data.get("outbound") or {}).get("fares") or []:
                parsed = _parse_fare(
                    fare, origin=query.origin, destination=query.destination
                )
                if parsed is not None:
                    options.append(parsed)
        return options

    def _get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            response = self._client.get(url, params=params, timeout=self.timeout)
        except httpx.TimeoutException as exc:
            raise FlightSearchError(f"Ryanair API timed out after {self.timeout}s") from exc
        except httpx.HTTPError as exc:
            raise APIError(f"Ryanair request failed: {exc}") from exc

        if response.status_code >= 400:
            raise APIError(
                f"Ryanair returned {response.status_code}: {response.text[:200]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise FlightSearchError("Ryanair returned non-JSON response") from exc


# ---- helpers --------------------------------------------------------------


def _months_spanning(start: date, end: date) -> list[date]:
    """Return a list of month-start dates covering [start, end] inclusive."""
    months: list[date] = []
    current = start.replace(day=1)
    last = end.replace(day=1)
    while current <= last:
        months.append(current)
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def _in_window(day: date, query: FlightSearch) -> bool:
    return query.date_from <= day <= query.date_to


def _parse_fare(
    fare: dict[str, Any], *, origin: str, destination: str
) -> FlightOption | None:
    """Parse one cheapestPerDay fare entry. Skips sold-out / unavailable days."""
    if fare.get("soldOut") or fare.get("unavailable"):
        return None
    price_obj = fare.get("price") or {}
    value = price_obj.get("value")
    if value is None:
        return None
    departure_str = fare.get("departureDate")
    if not departure_str:
        return None
    try:
        departure = datetime.fromisoformat(departure_str)
    except ValueError:
        return None

    day_iso = departure.date().isoformat()
    booking_url = (
        "https://www.ryanair.com/gb/en/trip/flights/select"
        f"?adults=1&dateOut={day_iso}&originIata={origin}&destinationIata={destination}"
    )

    return FlightOption(
        origin=origin,
        destination=destination,
        departure=departure,
        price=float(value),
        currency=price_obj.get("currencyCode", "EUR"),
        booking_url=booking_url,
    )


def _pair_round_trip(
    outbound: list[FlightOption],
    inbound: list[FlightOption],
    query: FlightSearch,
) -> list[FlightOption]:
    """Build round-trip options by pairing compatible outbound + inbound days.

    Ryanair's round-trip endpoint gives independent outbound/inbound lists
    (cheapest per day each direction). We combine them respecting nights_min
    and nights_max, using the sum as the round-trip price.
    """
    nights_min = query.nights_min if query.nights_min is not None else 0
    nights_max = query.nights_max if query.nights_max is not None else 60

    pairs: list[FlightOption] = []
    for out in outbound:
        if not _in_window(out.departure.date(), query):
            continue
        for ret in inbound:
            nights = (ret.departure.date() - out.departure.date()).days
            if nights < nights_min or nights > nights_max:
                continue
            pairs.append(
                FlightOption(
                    origin=out.origin,
                    destination=out.destination,
                    departure=out.departure,
                    return_departure=ret.departure,
                    price=out.price + ret.price,
                    currency=out.currency,
                    booking_url=out.booking_url,
                )
            )
    return pairs
