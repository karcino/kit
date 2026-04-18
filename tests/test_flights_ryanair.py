"""Tests for the Ryanair public fare API client."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import httpx
import pytest

from kit.errors import APIError, FlightSearchError
from kit.flights.core import FlightSearch
from kit.flights.ryanair import (
    RyanairFareClient,
    _months_spanning,
    _pair_round_trip,
    _parse_fare,
)


def _query(**kwargs) -> FlightSearch:
    defaults: dict = {
        "origin": "BER",
        "destination": "DUB",
        "date_from": date(2026, 5, 1),
        "date_to": date(2026, 5, 10),
    }
    defaults.update(kwargs)
    return FlightSearch(**defaults)


def _fare(day: str, price: float = 29.99, sold_out: bool = False) -> dict:
    return {
        "day": day,
        "departureDate": f"{day}T07:30:00",
        "arrivalDate": f"{day}T08:50:00",
        "price": {"value": price, "currencyCode": "EUR"},
        "soldOut": sold_out,
        "unavailable": False,
    }


class TestMonthsSpanning:
    def test_single_month(self):
        months = _months_spanning(date(2026, 5, 1), date(2026, 5, 31))
        assert months == [date(2026, 5, 1)]

    def test_two_months(self):
        months = _months_spanning(date(2026, 5, 15), date(2026, 6, 10))
        assert months == [date(2026, 5, 1), date(2026, 6, 1)]

    def test_year_boundary(self):
        months = _months_spanning(date(2026, 12, 15), date(2027, 2, 10))
        assert months == [date(2026, 12, 1), date(2027, 1, 1), date(2027, 2, 1)]


class TestParseFare:
    def test_parses_standard_fare(self):
        opt = _parse_fare(_fare("2026-05-03"), origin="BER", destination="DUB")
        assert opt is not None
        assert opt.price == 29.99
        assert opt.origin == "BER"
        assert opt.destination == "DUB"
        assert opt.currency == "EUR"
        assert "BER" in opt.booking_url and "DUB" in opt.booking_url
        assert "2026-05-03" in opt.booking_url

    def test_skips_sold_out(self):
        assert _parse_fare(
            _fare("2026-05-03", sold_out=True), origin="BER", destination="DUB"
        ) is None

    def test_skips_missing_price(self):
        fare = _fare("2026-05-03")
        fare["price"] = {}
        assert _parse_fare(fare, origin="BER", destination="DUB") is None

    def test_skips_bad_departure(self):
        fare = _fare("2026-05-03")
        fare["departureDate"] = "not-a-date"
        assert _parse_fare(fare, origin="BER", destination="DUB") is None


class TestRyanairFareClient:
    def _mock_response(self, payload: dict) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload
        return mock_resp

    def test_one_way_single_month(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = self._mock_response(
            {"outbound": {"fares": [_fare("2026-05-03"), _fare("2026-05-05", 39.99)]}}
        )
        client = RyanairFareClient(http_client=mock_client)

        options = client.run_search(_query())

        mock_client.get.assert_called_once()
        assert "oneWayFares/BER/DUB/cheapestPerDay" in mock_client.get.call_args.args[0]
        assert len(options) == 2

    def test_one_way_filters_date_window(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = self._mock_response({
            "outbound": {
                "fares": [
                    _fare("2026-05-01"),
                    _fare("2026-05-15"),  # outside window
                    _fare("2026-05-08"),
                ]
            }
        })
        client = RyanairFareClient(http_client=mock_client)

        options = client.run_search(_query(date_from=date(2026, 5, 1), date_to=date(2026, 5, 10)))

        days = {o.departure.date() for o in options}
        assert date(2026, 5, 15) not in days
        assert date(2026, 5, 1) in days and date(2026, 5, 8) in days

    def test_one_way_spans_multiple_months(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            self._mock_response({"outbound": {"fares": [_fare("2026-05-28", 30)]}}),
            self._mock_response({"outbound": {"fares": [_fare("2026-06-02", 40)]}}),
        ]
        client = RyanairFareClient(http_client=mock_client)

        options = client.run_search(_query(date_from=date(2026, 5, 28), date_to=date(2026, 6, 5)))

        assert mock_client.get.call_count == 2
        assert len(options) == 2

    def test_raises_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "service unavailable"
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_resp
        client = RyanairFareClient(http_client=mock_client)

        with pytest.raises(APIError):
            client.run_search(_query())

    def test_raises_on_timeout(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.TimeoutException("boom")
        client = RyanairFareClient(http_client=mock_client)

        with pytest.raises(FlightSearchError):
            client.run_search(_query())

    def test_raises_on_non_json(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_resp
        client = RyanairFareClient(http_client=mock_client)

        with pytest.raises(FlightSearchError):
            client.run_search(_query())


class TestPairRoundTrip:
    def test_pairs_within_nights_window(self):
        from datetime import datetime

        from kit.flights.core import FlightOption

        outbound = [
            FlightOption(
                origin="BER", destination="DUB",
                departure=datetime(2026, 5, 3, 7, 0),
                price=40.0, currency="EUR",
            )
        ]
        inbound = [
            FlightOption(
                origin="DUB", destination="BER",
                departure=datetime(2026, 5, 6, 19, 0),
                price=60.0, currency="EUR",
            ),
            FlightOption(
                origin="DUB", destination="BER",
                departure=datetime(2026, 5, 15, 19, 0),  # 12 nights — too long
                price=50.0, currency="EUR",
            ),
        ]
        query = _query(trip_type="round_trip", nights_min=2, nights_max=5)

        pairs = _pair_round_trip(outbound, inbound, query)

        assert len(pairs) == 1
        assert pairs[0].price == 100.0
        assert pairs[0].return_departure.date() == date(2026, 5, 6)
