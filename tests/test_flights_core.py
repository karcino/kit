"""Tests for flight search Pydantic models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from datetime import datetime

from kit.flights.core import FlightOption, FlightSearch
from kit.integrations import CalendarEventCandidate


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


class TestFlightOptionCandidate:
    def _opt(self, **overrides) -> FlightOption:
        base = dict(
            origin="BER",
            destination="DUB",
            departure=datetime(2026, 5, 3, 7, 30),
            price=42.99,
            currency="EUR",
            flight_number="FR1234",
            booking_url="https://ryanair.com/x",
        )
        base.update(overrides)
        return FlightOption(**base)

    def test_candidate_shape_one_way(self):
        cand = self._opt().as_calendar_event_candidate()
        assert isinstance(cand, CalendarEventCandidate)
        assert cand.title == "Flight BER→DUB"
        assert cand.start == datetime(2026, 5, 3, 7, 30)
        assert cand.end is None
        assert cand.duration_seconds == 2 * 60 * 60  # short-haul default
        assert cand.location == "BER"
        assert cand.source == "flight"
        assert cand.source_id == "FR1234"
        assert cand.booking_url == "https://ryanair.com/x"
        assert "42.99 EUR" in cand.description
        assert "BER → DUB" in cand.description

    def test_candidate_shape_round_trip(self):
        cand = self._opt(
            return_departure=datetime(2026, 5, 10, 18, 0),
        ).as_calendar_event_candidate()
        assert cand.end == datetime(2026, 5, 10, 18, 0)
        assert cand.duration_seconds is None

    def test_candidate_converts_to_calendar_event(self):
        event = self._opt().as_calendar_event_candidate().to_calendar_event()
        assert event.title == "Flight BER→DUB"
        assert event.duration_minutes == 120
        assert event.location == "BER"
        assert "Link: https://ryanair.com/x" in (event.description or "")
