"""Tests for the flights planner orchestrator."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

from kit.flights.core import FlightOption, FlightSearch
from kit.flights.planner import search_flights


def _query() -> FlightSearch:
    return FlightSearch(
        origin="BER",
        destination="DUB",
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 10),
    )


def _option(price: float, departure: datetime) -> FlightOption:
    return FlightOption(
        origin="BER",
        destination="DUB",
        departure=departure,
        price=price,
        currency="EUR",
    )


class TestSearchFlights:
    def test_sorts_by_price_then_departure(self):
        client = MagicMock()
        client.run_search.return_value = [
            _option(45.0, datetime(2026, 5, 3, 7, 0)),
            _option(29.99, datetime(2026, 5, 5, 9, 0)),
            _option(29.99, datetime(2026, 5, 4, 6, 0)),
        ]

        result = search_flights(_query(), client=client)

        assert [o.price for o in result.options] == [29.99, 29.99, 45.0]
        assert result.options[0].departure < result.options[1].departure
        assert result.cheapest.price == 29.99

    def test_empty_result_has_no_cheapest(self):
        client = MagicMock()
        client.run_search.return_value = []

        result = search_flights(_query(), client=client)

        assert result.options == []
        assert result.cheapest is None

    def test_caps_at_max_results(self):
        client = MagicMock()
        client.run_search.return_value = [
            _option(float(i), datetime(2026, 5, 1) + timedelta(days=i))
            for i in range(50)
        ]
        query = FlightSearch(
            origin="BER",
            destination="DUB",
            date_from=date(2026, 5, 1),
            date_to=date(2026, 6, 30),
            max_results=5,
        )

        result = search_flights(query, client=client)
        assert len(result.options) == 5

    def test_source_is_ryanair(self):
        client = MagicMock()
        client.run_search.return_value = []

        result = search_flights(_query(), client=client)
        assert result.source == "ryanair"
