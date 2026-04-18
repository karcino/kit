"""Tests for MCP server tool functions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from kit.cal.core import CalendarEvent, TravelBuffer
from kit.config import KitConfig
from kit.route.core import DeepLinks, RouteResult, RouteStep, TransportMode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TZ = timezone(timedelta(hours=1))


def _sample_route_result(**overrides) -> RouteResult:
    defaults = {
        "origin": "Alexanderplatz, Berlin",
        "destination": "Brandenburger Tor, Berlin",
        "mode": TransportMode.TRANSIT,
        "duration_seconds": 900,
        "departure": datetime(2026, 3, 25, 10, 0, tzinfo=_TZ),
        "arrival": datetime(2026, 3, 25, 10, 15, tzinfo=_TZ),
        "steps": [
            RouteStep(
                instruction="Take U5 towards Hauptbahnhof",
                mode="TRANSIT",
                distance_meters=3200,
                duration_seconds=600,
                transit_line="U5",
                transit_stops=3,
            ),
            RouteStep(
                instruction="Walk to Brandenburger Tor",
                mode="WALKING",
                distance_meters=400,
                duration_seconds=300,
            ),
        ],
        "deep_links": DeepLinks(
            google_maps="https://maps.google.com/?saddr=Alexanderplatz&daddr=Brandenburger+Tor",
            db_navigator="https://reiseauskunft.bahn.de/bin/query.exe/dn",
        ),
    }
    defaults.update(overrides)
    return RouteResult(**defaults)


@pytest.fixture
def mock_config():
    return KitConfig(
        google_maps_api_key="test-key-123",
        home="Alexanderplatz, Berlin",
        calendar_id="primary",
    )


@pytest.fixture
def sample_route():
    return _sample_route_result()


# ---------------------------------------------------------------------------
# Route tool tests
# ---------------------------------------------------------------------------


class TestKitRoute:
    """Tests for the kit_route MCP tool."""

    @patch("kit.route.mcp_tools.plan_route")
    def test_kit_route_returns_json(self, mock_plan, mock_config, sample_route):
        """kit_route should return valid JSON with route details."""
        mock_plan.return_value = sample_route

        from mcp.server.fastmcp import FastMCP
        from kit.route.mcp_tools import register_route_tools

        mcp = FastMCP("test")
        register_route_tools(mcp, mock_config)

        # Get the registered tool function
        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_route":
                tool_fn = t.fn
                break

        assert tool_fn is not None, "kit_route tool not registered"
        result = tool_fn("Alexanderplatz", "Brandenburger Tor")
        data = json.loads(result)

        assert data["origin"] == "Alexanderplatz, Berlin"
        assert data["destination"] == "Brandenburger Tor, Berlin"
        assert data["duration_seconds"] == 900
        assert len(data["steps"]) == 2
        assert "google_maps" in data["deep_links"]

    @patch("kit.route.mcp_tools.plan_route")
    def test_kit_route_passes_mode(self, mock_plan, mock_config, sample_route):
        """kit_route should pass the transport mode to plan_route."""
        mock_plan.return_value = sample_route

        from mcp.server.fastmcp import FastMCP
        from kit.route.mcp_tools import register_route_tools

        mcp = FastMCP("test")
        register_route_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_route":
                tool_fn = t.fn
                break

        tool_fn("A", "B", mode="driving")
        mock_plan.assert_called_once_with(
            "A", "B", mode=TransportMode.DRIVING, config=mock_config
        )


class TestKitRouteMulti:
    """Tests for the kit_route_multi MCP tool."""

    @patch("kit.route.mcp_tools.plan_multi_route")
    def test_kit_route_multi_returns_total(self, mock_multi, mock_config):
        """kit_route_multi should return total duration and per-leg details."""
        leg1 = _sample_route_result(duration_seconds=600)
        leg2 = _sample_route_result(
            origin="Brandenburger Tor",
            destination="Potsdamer Platz",
            duration_seconds=300,
        )
        mock_multi.return_value = [leg1, leg2]

        from mcp.server.fastmcp import FastMCP
        from kit.route.mcp_tools import register_route_tools

        mcp = FastMCP("test")
        register_route_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_route_multi":
                tool_fn = t.fn
                break

        assert tool_fn is not None, "kit_route_multi tool not registered"
        result = json.loads(tool_fn(["A", "B", "C"]))

        assert result["total_duration_seconds"] == 900
        assert result["total_duration_human"] == "15 min"
        assert len(result["legs"]) == 2

    @patch("kit.route.mcp_tools.plan_multi_route")
    def test_kit_route_multi_passes_mode(self, mock_multi, mock_config):
        """kit_route_multi should pass mode to plan_multi_route."""
        mock_multi.return_value = [_sample_route_result()]

        from mcp.server.fastmcp import FastMCP
        from kit.route.mcp_tools import register_route_tools

        mcp = FastMCP("test")
        register_route_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_route_multi":
                tool_fn = t.fn
                break

        tool_fn(["A", "B"], mode="walking")
        mock_multi.assert_called_once_with(
            ["A", "B"], mode=TransportMode.WALKING, config=mock_config
        )


# ---------------------------------------------------------------------------
# Calendar tool tests
# ---------------------------------------------------------------------------


class TestKitCalAdd:
    """Tests for the kit_cal_add MCP tool."""

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_kit_cal_add_creates_event(self, MockCalClient, mock_config):
        """kit_cal_add should create a calendar event and return JSON."""
        mock_client = MockCalClient.return_value
        mock_client.add_event.return_value = {"id": "evt_123", "status": "confirmed"}

        from mcp.server.fastmcp import FastMCP
        from kit.cal.mcp_tools import register_cal_tools

        mcp = FastMCP("test")
        register_cal_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_cal_add":
                tool_fn = t.fn
                break

        assert tool_fn is not None, "kit_cal_add tool not registered"
        result = json.loads(tool_fn(title="Meeting", start="14:00", date="2026-03-25"))

        assert result["event"]["title"] == "Meeting"
        assert result["event"]["id"] == "evt_123"
        mock_client.add_event.assert_called_once()

    @patch("kit.cal.mcp_tools.plan_route")
    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_kit_cal_add_with_travel_buffer(self, MockCalClient, mock_plan, mock_config):
        """kit_cal_add should create a travel buffer when route_from is set."""
        mock_client = MockCalClient.return_value
        mock_client.add_event.return_value = {"id": "evt_456"}
        mock_client.add_travel_buffer.return_value = {"id": "buf_789"}
        mock_plan.return_value = _sample_route_result()

        from mcp.server.fastmcp import FastMCP
        from kit.cal.mcp_tools import register_cal_tools

        mcp = FastMCP("test")
        register_cal_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_cal_add":
                tool_fn = t.fn
                break

        result = json.loads(
            tool_fn(
                title="Meeting",
                start="14:00",
                date="2026-03-25",
                location="Brandenburger Tor",
                route_from="Alexanderplatz",
            )
        )

        assert result["travel_buffer"] is not None
        assert result["travel_buffer"]["duration"] == "15 min"
        mock_client.add_travel_buffer.assert_called_once()


class TestKitCalToday:
    """Tests for the kit_cal_today MCP tool."""

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_kit_cal_today_returns_events(self, MockCalClient, mock_config):
        """kit_cal_today should list today's events."""
        mock_client = MockCalClient.return_value
        mock_client.list_events.return_value = [
            {"summary": "Standup", "start": {"dateTime": "2026-03-25T09:00:00+01:00"}},
            {"summary": "Lunch", "start": {"dateTime": "2026-03-25T12:00:00+01:00"}},
        ]

        from mcp.server.fastmcp import FastMCP
        from kit.cal.mcp_tools import register_cal_tools

        mcp = FastMCP("test")
        register_cal_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_cal_today":
                tool_fn = t.fn
                break

        assert tool_fn is not None, "kit_cal_today tool not registered"
        result = json.loads(tool_fn())

        assert len(result) == 2
        assert result[0]["summary"] == "Standup"


class TestKitCalList:
    """Tests for the kit_cal_list MCP tool."""

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_kit_cal_list_custom_range(self, MockCalClient, mock_config):
        """kit_cal_list should accept custom date range."""
        mock_client = MockCalClient.return_value
        mock_client.list_events.return_value = []

        from mcp.server.fastmcp import FastMCP
        from kit.cal.mcp_tools import register_cal_tools

        mcp = FastMCP("test")
        register_cal_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_cal_list":
                tool_fn = t.fn
                break

        assert tool_fn is not None, "kit_cal_list tool not registered"
        result = json.loads(
            tool_fn(
                start_date="2026-03-25T00:00:00+01:00",
                end_date="2026-03-26T00:00:00+01:00",
            )
        )

        assert result == []
        mock_client.list_events.assert_called_once()

    @patch("kit.cal.mcp_tools.GoogleCalendarClient")
    def test_kit_cal_list_week(self, MockCalClient, mock_config):
        """kit_cal_list with range='week' should query a 7-day window."""
        mock_client = MockCalClient.return_value
        mock_client.list_events.return_value = []

        from mcp.server.fastmcp import FastMCP
        from kit.cal.mcp_tools import register_cal_tools

        mcp = FastMCP("test")
        register_cal_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_cal_list":
                tool_fn = t.fn
                break

        tool_fn(range="week")
        call_args = mock_client.list_events.call_args
        # time_max should be ~7 days after time_min
        assert call_args is not None


# ---------------------------------------------------------------------------
# Plan day tool tests
# ---------------------------------------------------------------------------


class TestKitPlanDay:
    """Tests for the kit_plan_day MCP tool."""

    def test_kit_plan_day_simple_tasks(self, mock_config):
        """kit_plan_day should schedule tasks sequentially without locations."""
        from mcp.server.fastmcp import FastMCP
        from kit.cal.mcp_tools import register_cal_tools

        mcp = FastMCP("test")
        register_cal_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_plan_day":
                tool_fn = t.fn
                break

        assert tool_fn is not None, "kit_plan_day tool not registered"
        result = json.loads(
            tool_fn(tasks=["Email beantworten", "Code Review", "Mittagspause"], date="2026-03-25")
        )

        assert result["date"] == "2026-03-25"
        assert len(result["schedule"]) == 3
        assert result["schedule"][0]["time"] == "09:00"
        assert result["schedule"][1]["time"] == "10:00"
        assert result["schedule"][2]["time"] == "11:00"

    @patch("kit.route.planner.plan_route")
    def test_kit_plan_day_with_locations(self, mock_plan, mock_config):
        """kit_plan_day should add travel time between located tasks."""
        mock_plan.return_value = _sample_route_result(duration_seconds=1800)  # 30 min

        from mcp.server.fastmcp import FastMCP
        from kit.cal.mcp_tools import register_cal_tools

        mcp = FastMCP("test")
        register_cal_tools(mcp, mock_config)

        tool_fn = None
        for t in mcp._tool_manager._tools.values():
            if t.name == "kit_plan_day":
                tool_fn = t.fn
                break

        result = json.loads(
            tool_fn(
                tasks=[
                    "Meeting @ Alexanderplatz",
                    "Workshop @ Potsdamer Platz",
                ],
                date="2026-03-25",
            )
        )

        schedule = result["schedule"]
        assert len(schedule) == 2
        # First task at 09:00
        assert schedule[0]["time"] == "09:00"
        assert schedule[0]["location"] == "Alexanderplatz"
        # Second task should be offset by 1h (task) + 30min (travel) + 5min (buffer) = 10:35
        assert schedule[1]["time"] == "10:35"
        assert schedule[1]["travel"] is not None
        assert schedule[1]["travel"]["duration_minutes"] == 30


# ---------------------------------------------------------------------------
# MCP server integration tests
# ---------------------------------------------------------------------------


class TestMCPServerIntegration:
    """Tests for the MCP server module setup."""

    def test_mcp_server_has_all_tools(self):
        """The MCP server should register all expected tools."""
        # Import triggers tool registration
        from kit.mcp_server import mcp as server

        tool_names = set(server._tool_manager._tools.keys())
        expected = {
            "kit_route",
            "kit_route_multi",
            "kit_cal_add",
            "kit_cal_today",
            "kit_cal_list",
            "kit_plan_day",
            "kit_flight_search",
            "kit_youtube_transcript",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    def test_run_function_exists(self):
        """The run() entry-point should be importable."""
        from kit.mcp_server import run

        assert callable(run)

    def test_tools_have_descriptions(self):
        """All tools should have non-empty descriptions."""
        from kit.mcp_server import mcp as server

        for name, tool in server._tool_manager._tools.items():
            assert tool.description, f"Tool {name} has no description"
            assert len(tool.description) > 20, f"Tool {name} description too short"
