"""Tests for calendar core models."""

import pytest
from datetime import datetime, timezone, timedelta

from kit.cal.core import CalendarEvent, TravelBuffer


CET = timezone(timedelta(hours=1))


class TestCalendarEvent:
    def test_basic_event(self):
        ev = CalendarEvent(
            title="Dinner",
            start=datetime(2026, 3, 25, 19, 0, tzinfo=CET),
            duration_minutes=60,
            location="Oranienstr 42",
        )
        assert ev.end.hour == 20
        assert ev.end.tzinfo == CET

    def test_default_duration(self):
        ev = CalendarEvent(
            title="Meeting",
            start=datetime(2026, 3, 25, 10, 0, tzinfo=CET),
        )
        assert ev.duration_minutes == 60
        assert ev.end == datetime(2026, 3, 25, 11, 0, tzinfo=CET)

    def test_custom_duration(self):
        ev = CalendarEvent(
            title="Workshop",
            start=datetime(2026, 3, 25, 14, 0, tzinfo=CET),
            duration_minutes=120,
        )
        assert ev.end == datetime(2026, 3, 25, 16, 0, tzinfo=CET)

    def test_all_day_event(self):
        ev = CalendarEvent(title="Urlaub", all_day=True, date="2026-03-25")
        assert ev.all_day is True
        assert ev.date == "2026-03-25"
        assert ev.end is None  # no start → no computed end

    def test_no_start_yields_none_end(self):
        ev = CalendarEvent(title="Placeholder")
        assert ev.start is None
        assert ev.end is None

    def test_default_calendar_id(self):
        ev = CalendarEvent(title="Test")
        assert ev.calendar_id == "primary"

    def test_optional_fields_default_none(self):
        ev = CalendarEvent(title="Bare")
        assert ev.location is None
        assert ev.description is None

    def test_full_event(self):
        ev = CalendarEvent(
            title="Full Event",
            start=datetime(2026, 3, 25, 9, 0, tzinfo=CET),
            duration_minutes=90,
            location="TU Berlin",
            description="Important meeting",
            calendar_id="work",
        )
        assert ev.title == "Full Event"
        assert ev.location == "TU Berlin"
        assert ev.description == "Important meeting"
        assert ev.calendar_id == "work"
        assert ev.end == datetime(2026, 3, 25, 10, 30, tzinfo=CET)


class TestTravelBuffer:
    def test_basic_buffer(self):
        buf = TravelBuffer(
            title="Anreise: Dinner",
            start=datetime(2026, 3, 25, 18, 33, tzinfo=CET),
            end=datetime(2026, 3, 25, 18, 55, tzinfo=CET),
            description="U8 · 22 min\nhttps://maps.google.com/...",
        )
        assert "Anreise" in buf.title
        assert buf.end > buf.start

    def test_default_description_empty(self):
        buf = TravelBuffer(
            title="Anreise",
            start=datetime(2026, 3, 25, 8, 0, tzinfo=CET),
            end=datetime(2026, 3, 25, 8, 30, tzinfo=CET),
        )
        assert buf.description == ""

    def test_default_calendar_id(self):
        buf = TravelBuffer(
            title="Buffer",
            start=datetime(2026, 3, 25, 8, 0, tzinfo=CET),
            end=datetime(2026, 3, 25, 8, 30, tzinfo=CET),
        )
        assert buf.calendar_id == "primary"
