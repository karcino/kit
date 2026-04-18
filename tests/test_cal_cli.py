"""CLI integration tests for kit cal commands."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kit.cli import app

runner = CliRunner()

CET = timezone(timedelta(hours=1))


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_EVENTS = [
    {
        "id": "ev1",
        "summary": "Team Standup",
        "start": {"dateTime": "2026-03-25T10:00:00+01:00"},
        "end": {"dateTime": "2026-03-25T10:30:00+01:00"},
        "location": "Zoom",
    },
    {
        "id": "ev2",
        "summary": "Lunch with Anna",
        "start": {"dateTime": "2026-03-25T12:30:00+01:00"},
        "end": {"dateTime": "2026-03-25T13:30:00+01:00"},
        "location": "Oranienstr 42",
    },
    {
        "id": "ev3",
        "summary": "Urlaub",
        "start": {"date": "2026-03-25"},
        "end": {"date": "2026-03-26"},
        "location": "",
    },
]


def _mock_client():
    """Create a mock GoogleCalendarClient."""
    client = MagicMock()
    client.add_event.return_value = {"id": "new-event-1", "summary": "Test"}
    client.add_travel_buffer.return_value = {"id": "buf-1", "summary": "Buffer"}
    client.list_events.return_value = SAMPLE_EVENTS
    client.delete_event.return_value = None
    return client


# ---------------------------------------------------------------------------
# cal --help
# ---------------------------------------------------------------------------

class TestCalHelp:
    def test_cal_help(self):
        result = runner.invoke(app, ["cal", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "today" in result.output
        assert "tomorrow" in result.output

    def test_cal_no_args_shows_help(self):
        result = runner.invoke(app, ["cal"])
        assert "add" in result.output or "Usage" in result.output


# ---------------------------------------------------------------------------
# cal add
# ---------------------------------------------------------------------------

class TestCalAdd:
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_basic_event(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, [
            "cal", "add", "Team Meeting", "--at", "14:00",
        ])

        assert result.exit_code == 0
        assert "Team Meeting" in result.output
        mock.add_event.assert_called_once()
        event = mock.add_event.call_args[0][0]
        assert event.title == "Team Meeting"
        assert event.start.hour == 14
        assert event.start.minute == 0

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_with_duration(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, [
            "cal", "add", "Workshop", "--at", "10:00", "--duration", "90",
        ])

        assert result.exit_code == 0
        event = mock.add_event.call_args[0][0]
        assert event.duration_minutes == 90

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_with_location(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, [
            "cal", "add", "Dinner", "--at", "19:00", "--location", "Alexanderplatz",
        ])

        assert result.exit_code == 0
        event = mock.add_event.call_args[0][0]
        assert event.location == "Alexanderplatz"

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_all_day_event(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, [
            "cal", "add", "Urlaub",
        ])

        assert result.exit_code == 0
        event = mock.add_event.call_args[0][0]
        assert event.all_day is True

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_json_output(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, [
            "cal", "add", "Meeting", "--at", "14:00", "--json",
        ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "new-event-1"

    @patch("kit.cal.commands.plan_route")
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_with_route_from(self, MockClient, mock_plan_route):
        mock = _mock_client()
        MockClient.return_value = mock

        # Mock route result
        from kit.route.core import RouteResult, DeepLinks, RouteStep, TransportMode
        mock_plan_route.return_value = RouteResult(
            origin="Home",
            destination="Alexanderplatz",
            mode=TransportMode.TRANSIT,
            duration_seconds=1800,  # 30 min
            departure=datetime(2026, 3, 25, 13, 25, tzinfo=CET),
            arrival=datetime(2026, 3, 25, 13, 55, tzinfo=CET),
            steps=[RouteStep(
                instruction="U8", mode="transit",
                distance_meters=5000, duration_seconds=1800,
            )],
            deep_links=DeepLinks(google_maps="https://maps.google.com"),
        )

        result = runner.invoke(app, [
            "cal", "add", "Dinner", "--at", "14:00",
            "--location", "Alexanderplatz", "--route-from", "home",
        ])

        assert result.exit_code == 0
        # Both event and travel buffer should be created
        mock.add_event.assert_called_once()
        mock.add_travel_buffer.assert_called_once()
        buffer = mock.add_travel_buffer.call_args[0][0]
        assert "Anreise" in buffer.title

    @patch("kit.cal.commands.plan_route")
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_route_from_failure_still_creates_event(self, MockClient, mock_plan_route):
        """If route planning fails, event should still be created."""
        mock = _mock_client()
        MockClient.return_value = mock
        from kit.errors import ConfigError
        mock_plan_route.side_effect = ConfigError("No API key")

        result = runner.invoke(app, [
            "cal", "add", "Dinner", "--at", "14:00",
            "--location", "Alexanderplatz", "--route-from", "home",
        ])

        assert result.exit_code == 0
        mock.add_event.assert_called_once()
        mock.add_travel_buffer.assert_not_called()

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_add_error_handling(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock
        from kit.errors import CalendarError
        mock.add_event.side_effect = CalendarError("API down")

        result = runner.invoke(app, [
            "cal", "add", "Fail", "--at", "10:00",
        ])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# cal today / cal tomorrow
# ---------------------------------------------------------------------------

class TestCalToday:
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_today_shows_events(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "today"])

        assert result.exit_code == 0
        assert "Team Standup" in result.output
        assert "Lunch with Anna" in result.output
        mock.list_events.assert_called_once()

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_today_no_events(self, MockClient):
        mock = _mock_client()
        mock.list_events.return_value = []
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "today"])

        assert result.exit_code == 0
        assert "No events" in result.output or "Keine" in result.output

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_today_json(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "today", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_today_error_handling(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock
        from kit.errors import CalendarError
        mock.list_events.side_effect = CalendarError("Auth failed")

        result = runner.invoke(app, ["cal", "today"])

        assert result.exit_code != 0


class TestCalTomorrow:
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_tomorrow_shows_events(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "tomorrow"])

        assert result.exit_code == 0
        mock.list_events.assert_called_once()

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_tomorrow_json(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "tomorrow", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)


class TestCalWeek:
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_week_shows_events(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "week"])

        assert result.exit_code == 0
        assert "Team Standup" in result.output
        mock.list_events.assert_called_once()
        # Spans a 7-day window
        kwargs = mock.list_events.call_args[1]
        assert "time_min" in kwargs and "time_max" in kwargs

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_week_json(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "week", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_week_no_events(self, MockClient):
        mock = _mock_client()
        mock.list_events.return_value = []
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "week"])

        assert result.exit_code == 0
        assert "No events" in result.output

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_week_error_handling(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock
        from kit.errors import CalendarError
        mock.list_events.side_effect = CalendarError("Auth failed")

        result = runner.invoke(app, ["cal", "week"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# cal list --date
# ---------------------------------------------------------------------------

class TestCalList:
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_list_specific_date(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "list", "--date", "2026-03-28"])

        assert result.exit_code == 0
        mock.list_events.assert_called_once()
        # Verify date range was passed
        call_kwargs = mock.list_events.call_args[1]
        assert "2026-03-28" in call_kwargs["time_min"]
        assert "2026-03-28" in call_kwargs["time_max"]

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_list_defaults_to_today(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "list"])

        assert result.exit_code == 0
        mock.list_events.assert_called_once()

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_list_json(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# cal delete
# ---------------------------------------------------------------------------

class TestCalDelete:
    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_delete_event(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "delete", "ev1"])

        assert result.exit_code == 0
        mock.delete_event.assert_called_once_with("ev1")

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_delete_json_output(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock

        result = runner.invoke(app, ["cal", "delete", "ev1", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["deleted"] == "ev1"

    @patch("kit.cal.commands.GoogleCalendarClient")
    def test_delete_error_handling(self, MockClient):
        mock = _mock_client()
        MockClient.return_value = mock
        from kit.errors import CalendarError
        mock.delete_event.side_effect = CalendarError("Not found")

        result = runner.invoke(app, ["cal", "delete", "missing"])

        assert result.exit_code != 0
