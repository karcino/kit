"""Tests for the kit_flight_search MCP tool."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from kit.config import KitConfig
from kit.flights.core import FlightOption, FlightSearch, FlightSearchResult


@pytest.fixture
def mock_config():
    return KitConfig()


def _sample_result() -> FlightSearchResult:
    opt = FlightOption(
        origin="BER",
        destination="DUB",
        departure=datetime(2026, 5, 3, 7, 30),
        price=29.99,
        currency="EUR",
    )
    query = FlightSearch(
        origin="BER",
        destination="DUB",
        date_from=datetime(2026, 5, 1).date(),
        date_to=datetime(2026, 5, 10).date(),
    )
    return FlightSearchResult(
        query=query,
        options=[opt],
        cheapest=opt,
        searched_at=datetime(2026, 4, 18, 12, 0, tzinfo=UTC),
    )


class TestKitFlightSearch:
    @patch("kit.flights.mcp_tools.search_flights")
    def test_returns_json(self, mock_search, mock_config):
        mock_search.return_value = _sample_result()

        from mcp.server.fastmcp import FastMCP

        from kit.flights.mcp_tools import register_flights_tools

        mcp = FastMCP("test")
        register_flights_tools(mcp, mock_config)

        tool_fn = next(
            t.fn for t in mcp._tool_manager._tools.values()
            if t.name == "kit_flight_search"
        )
        result = tool_fn(
            origin="BER",
            destination="DUB",
            date_from="2026-05-01",
            date_to="2026-05-10",
        )
        data = json.loads(result)
        assert data["cheapest"]["price"] == 29.99
        assert data["source"] == "ryanair"

    @patch("kit.flights.mcp_tools.search_flights")
    def test_parses_dates_and_trip_type(self, mock_search, mock_config):
        mock_search.return_value = _sample_result()

        from mcp.server.fastmcp import FastMCP

        from kit.flights.mcp_tools import register_flights_tools

        mcp = FastMCP("test")
        register_flights_tools(mcp, mock_config)

        tool_fn = next(
            t.fn for t in mcp._tool_manager._tools.values()
            if t.name == "kit_flight_search"
        )
        tool_fn(
            origin="BER",
            destination="DUB",
            date_from="2026-05-01",
            date_to="2026-05-30",
            trip_type="round_trip",
            nights_min=3,
            nights_max=7,
        )
        call_query = mock_search.call_args.args[0]
        assert call_query.trip_type == "round_trip"
        assert call_query.nights_min == 3
        assert call_query.nights_max == 7
