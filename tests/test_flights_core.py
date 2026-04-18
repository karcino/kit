"""Tests for flight search Pydantic models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from kit.flights.core import FlightSearch


class TestFlightSearch:
    def test_minimal_one_way(self):
        q = FlightSearch(
            origin="BER",
            destination="DUB",
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 10),
        )
        assert q.trip_type == "one_way"
        assert q.max_results == 20

    def test_rejects_inverted_dates(self):
        with pytest.raises(ValidationError):
            FlightSearch(
                origin="BER",
                destination="DUB",
                date_from=date(2026, 5, 10),
                date_to=date(2026, 5, 1),
            )

    def test_rejects_inverted_nights(self):
        with pytest.raises(ValidationError):
            FlightSearch(
                origin="BER",
                destination="DUB",
                date_from=date(2026, 5, 1),
                date_to=date(2026, 5, 30),
                trip_type="round_trip",
                nights_min=7,
                nights_max=3,
            )

    def test_round_trip_with_valid_nights(self):
        q = FlightSearch(
            origin="BER",
            destination="DUB",
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 30),
            trip_type="round_trip",
            nights_min=3,
            nights_max=7,
        )
        assert q.nights_min == 3
        assert q.nights_max == 7
