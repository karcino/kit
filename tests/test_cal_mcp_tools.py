"""Tests for kit.cal.mcp_tools — focused on kit_cal_add_from_candidate.

Verifies the cross-tool Pydantic interchange (option d) wiring:
a ``CalendarEventCandidate`` → ``CalendarEvent`` → ``GoogleCalendarClient.add_event``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from kit.config import KitConfig
from kit.errors import CalendarError
from kit.integrations import CalendarEventCandidate

CET = timezone(timedelta(hours=1))


@pytest.fixture
def mock_config() -> KitConfig:
    return KitConfig()


def _tool(mock_config: KitConfig, name: str = "kit_cal_add_from_candidate"):
    """Register cal tools on a fresh FastMCP and return the named tool fn."""
    from mcp.server.fastmcp import FastMCP

    from kit.cal.mcp_tools import register_cal_tools

    mcp = FastMCP("test")
    register_cal_tools(mcp, mock_config)
    return next(t.fn for t in mcp._tool_manager._tools.values() if t.name == name)


class TestCalendarEventCandidateAdapter:
    """Unit tests for CalendarEventCandidate.to_calendar_event() (no MCP)."""

    def test_end_takes_precedence_over_duration(self) -> None:
        cand = CalendarEventCandidate(
            title="Flight BER→DUB",
            start=datetime(2026, 5, 3, 7, 30, tzinfo=CET),
            end=datetime(2026, 5, 3, 9, 45, tzinfo=CET),
            duration_seconds=99999,  # must be ignored when end is set
            location="DUB",
            description="29.99 EUR",
            source="flight",
            booking_url="https://www.ryanair.com/book/abc",
        )
        event = cand.to_calendar_event()
        assert event.title == "Flight BER→DUB"
        assert event.duration_minutes == 135  # 2h15 = 135 min
        assert event.location == "DUB"
        assert "29.99 EUR" in event.description
        assert "https://www.ryanair.com/book/abc" in event.description

    def test_duration_seconds_used_when_no_end(self) -> None:
        cand = CalendarEventCandidate(
            title="Transit",
            start=datetime(2026, 5, 3, 7, 30, tzinfo=CET),
            duration_seconds=1800,  # 30 min
        )
        event = cand.to_calendar_event()
        assert event.duration_minutes == 30

    def test_end_before_start_raises(self) -> None:
        cand = CalendarEventCandidate(
            title="Bad",
            start=datetime(2026, 5, 3, 10, 0, tzinfo=CET),
            end=datetime(2026, 5, 3, 9, 0, tzinfo=CET),
        )
        with pytest.raises(CalendarError, match="before start"):
            cand.to_calendar_event()


class TestKitCalAddFromCandidate:
    """MCP-level tests with a mocked GoogleCalendarClient."""

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_creates_event_from_iso_fields(self, mock_cls: MagicMock, mock_config: KitConfig) -> None:
        client = mock_cls.return_value
        client.add_event.return_value = {"id": "evt-1", "summary": "Flight BER→DUB"}

        tool_fn = _tool(mock_config)
        result = tool_fn(
            title="Flight BER→DUB",
            start="2026-05-03T07:30:00+01:00",
            end="2026-05-03T09:45:00+01:00",
            location="DUB",
            description="29.99 EUR",
            source="flight",
            source_id="FR1234",
            booking_url="https://www.ryanair.com/book/abc",
        )
        data = json.loads(result)

        # Response shape
        assert data["event"]["id"] == "evt-1"
        assert data["event"]["title"] == "Flight BER→DUB"
        assert data["event"]["location"] == "DUB"
        assert data["candidate"]["source"] == "flight"
        assert data["candidate"]["source_id"] == "FR1234"

        # add_event called with the correct derived CalendarEvent
        client.add_event.assert_called_once()
        (event_arg,), _ = client.add_event.call_args
        assert event_arg.title == "Flight BER→DUB"
        assert event_arg.duration_minutes == 135
        assert event_arg.location == "DUB"
        assert "https://www.ryanair.com/book/abc" in (event_arg.description or "")

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_uses_duration_seconds_fallback(self, mock_cls: MagicMock, mock_config: KitConfig) -> None:
        client = mock_cls.return_value
        client.add_event.return_value = {"id": "evt-2"}

        tool_fn = _tool(mock_config)
        tool_fn(
            title="Briefing",
            start="2026-05-03T07:30:00+01:00",
            duration_seconds=900,  # 15 min
        )
        (event_arg,), _ = client.add_event.call_args
        assert event_arg.duration_minutes == 15

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_invalid_start_raises_calendar_error(
        self, mock_cls: MagicMock, mock_config: KitConfig
    ) -> None:
        tool_fn = _tool(mock_config)
        with pytest.raises(CalendarError, match="Invalid 'start'"):
            tool_fn(title="x", start="not-a-datetime")
        mock_cls.return_value.add_event.assert_not_called()


class TestFlightToCalendarChain:
    """End-to-end sanity: FlightOption → candidate → cal MCP tool."""

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_flight_option_chains_into_cal_tool(
        self, mock_cls: MagicMock, mock_config: KitConfig
    ) -> None:
        from kit.flights.core import FlightOption

        mock_cls.return_value.add_event.return_value = {"id": "evt-chain"}

        flight = FlightOption(
            origin="BER",
            destination="DUB",
            departure=datetime(2026, 5, 3, 7, 30, tzinfo=CET),
            price=29.99,
            flight_number="FR1234",
            booking_url="https://www.ryanair.com/book/abc",
        )
        candidate = flight.as_calendar_event_candidate()
        payload = candidate.model_dump(mode="json")

        tool_fn = _tool(mock_config)
        result = tool_fn(**{k: v for k, v in payload.items() if k != "duration_seconds"})
        data = json.loads(result)

        assert data["event"]["id"] == "evt-chain"
        assert data["candidate"]["source"] == "flight"
        assert data["candidate"]["source_id"] == "FR1234"
