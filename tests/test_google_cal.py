"""Tests for Google Calendar client (mocked API)."""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from kit.cal.core import CalendarEvent, TravelBuffer
from kit.cal.google_cal import GoogleCalendarClient
from kit.errors import CalendarError


CET = timezone(timedelta(hours=1))


@pytest.fixture
def tmp_creds_dir(tmp_path):
    """Create a temporary credentials directory with a fake token."""
    token_data = {
        "token": "fake-access-token",
        "refresh_token": "fake-refresh-token",
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret",
    }
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps(token_data))
    return tmp_path


@pytest.fixture
def mock_service():
    """Create a mock Google Calendar service."""
    service = MagicMock()
    return service


@pytest.fixture
def client(tmp_creds_dir, mock_service):
    """Create a GoogleCalendarClient with mocked service."""
    c = GoogleCalendarClient(credentials_dir=tmp_creds_dir)
    c._service = mock_service
    return c


class TestAddEvent:
    def test_timed_event(self, client, mock_service):
        event = CalendarEvent(
            title="Dinner",
            start=datetime(2026, 3, 25, 19, 0, tzinfo=CET),
            duration_minutes=60,
            location="Oranienstr 42",
            description="With friends",
        )
        mock_service.events().insert().execute.return_value = {
            "id": "abc123",
            "summary": "Dinner",
        }

        result = client.add_event(event)

        assert result["id"] == "abc123"
        mock_service.events().insert.assert_called()
        call_kwargs = mock_service.events().insert.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body["summary"] == "Dinner"
        assert "dateTime" in body["start"]
        assert body["location"] == "Oranienstr 42"

    def test_all_day_event(self, client, mock_service):
        event = CalendarEvent(
            title="Urlaub",
            all_day=True,
            date="2026-03-25",
        )
        mock_service.events().insert().execute.return_value = {
            "id": "allday1",
            "summary": "Urlaub",
        }

        result = client.add_event(event)

        assert result["id"] == "allday1"
        call_kwargs = mock_service.events().insert.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body["start"] == {"date": "2026-03-25"}
        assert body["end"] == {"date": "2026-03-25"}

    def test_missing_start_raises(self, client):
        event = CalendarEvent(title="Bad Event")
        with pytest.raises(CalendarError, match="start time or be all-day"):
            client.add_event(event)

    def test_api_error_wrapped(self, client, mock_service):
        event = CalendarEvent(
            title="Fail",
            start=datetime(2026, 3, 25, 10, 0, tzinfo=CET),
        )
        mock_service.events().insert().execute.side_effect = Exception("API down")

        with pytest.raises(CalendarError, match="Failed to create event"):
            client.add_event(event)


class TestAddTravelBuffer:
    def test_creates_buffer(self, client, mock_service):
        buf = TravelBuffer(
            title="Anreise: Dinner",
            start=datetime(2026, 3, 25, 18, 33, tzinfo=CET),
            end=datetime(2026, 3, 25, 18, 55, tzinfo=CET),
            description="U8 · 22 min",
        )
        mock_service.events().insert().execute.return_value = {
            "id": "buf1",
            "summary": "\U0001f687 Anreise: Dinner",
        }

        result = client.add_travel_buffer(buf)

        assert result["id"] == "buf1"
        call_kwargs = mock_service.events().insert.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert "\U0001f687" in body["summary"]
        assert body["colorId"] == "8"

    def test_api_error_wrapped(self, client, mock_service):
        buf = TravelBuffer(
            title="Fail",
            start=datetime(2026, 3, 25, 18, 0, tzinfo=CET),
            end=datetime(2026, 3, 25, 18, 30, tzinfo=CET),
        )
        mock_service.events().insert().execute.side_effect = Exception("timeout")

        with pytest.raises(CalendarError, match="Failed to create travel buffer"):
            client.add_travel_buffer(buf)


class TestListEvents:
    def test_list_returns_items(self, client, mock_service):
        mock_service.events().list().execute.return_value = {
            "items": [
                {"id": "ev1", "summary": "Meeting"},
                {"id": "ev2", "summary": "Lunch"},
            ]
        }

        result = client.list_events()

        assert len(result) == 2
        assert result[0]["summary"] == "Meeting"

    def test_list_with_time_range(self, client, mock_service):
        mock_service.events().list().execute.return_value = {"items": []}

        result = client.list_events(
            time_min="2026-03-25T00:00:00+01:00",
            time_max="2026-03-25T23:59:59+01:00",
        )

        assert result == []
        mock_service.events().list.assert_called()

    def test_list_empty(self, client, mock_service):
        mock_service.events().list().execute.return_value = {"items": []}

        result = client.list_events()

        assert result == []

    def test_api_error_wrapped(self, client, mock_service):
        mock_service.events().list().execute.side_effect = Exception("network")

        with pytest.raises(CalendarError, match="Failed to list events"):
            client.list_events()


class TestDeleteEvent:
    def test_delete_calls_api(self, client, mock_service):
        mock_service.events().delete().execute.return_value = None

        client.delete_event("abc123")

        mock_service.events().delete.assert_called()

    def test_api_error_wrapped(self, client, mock_service):
        mock_service.events().delete().execute.side_effect = Exception("not found")

        with pytest.raises(CalendarError, match="Failed to delete event"):
            client.delete_event("missing")


class TestAuth:
    def test_missing_token_raises(self, tmp_path):
        """Client without token.json raises CalendarError."""
        c = GoogleCalendarClient(credentials_dir=tmp_path)
        with pytest.raises(CalendarError, match="Not authenticated"):
            c._get_service()

    def test_setup_missing_credentials_raises(self, tmp_path):
        """Setup without credentials.json raises CalendarError."""
        with pytest.raises(CalendarError, match="client_secrets"):
            GoogleCalendarClient.setup(credentials_dir=tmp_path)
