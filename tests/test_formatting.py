"""Tests for kit.utils.formatting — Rich-based output formatting."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from kit.route.core import DeepLinks, RouteResult, RouteStep, TransportMode
from kit.utils.formatting import (
    format_distance,
    format_duration,
    print_route,
    print_route_json,
)


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------

class TestFormatDuration:
    def test_minutes_only(self):
        assert format_duration(2700) == "45 min"

    def test_hours_and_minutes(self):
        assert format_duration(5400) == "1h 30min"

    def test_exact_hour(self):
        assert format_duration(3600) == "1h 0min"

    def test_zero_seconds(self):
        assert format_duration(0) == "0 min"

    def test_less_than_a_minute(self):
        assert format_duration(30) == "0 min"

    def test_multiple_hours(self):
        assert format_duration(7800) == "2h 10min"


# ---------------------------------------------------------------------------
# format_distance
# ---------------------------------------------------------------------------

class TestFormatDistance:
    def test_meters_below_threshold(self):
        assert format_distance(450) == "450 m"

    def test_exactly_1000(self):
        assert format_distance(1000) == "1.0 km"

    def test_kilometers(self):
        assert format_distance(2300) == "2.3 km"

    def test_large_distance(self):
        assert format_distance(12456) == "12.5 km"

    def test_zero(self):
        assert format_distance(0) == "0 m"

    def test_just_below_km(self):
        assert format_distance(999) == "999 m"


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

CET = timezone(timedelta(hours=1))


@pytest.fixture()
def sample_route() -> RouteResult:
    return RouteResult(
        origin="Alexanderplatz, Berlin",
        destination="Kottbusser Tor, Berlin",
        mode=TransportMode.TRANSIT,
        duration_seconds=900,
        departure=datetime(2026, 3, 25, 18, 0, tzinfo=CET),
        arrival=datetime(2026, 3, 25, 18, 15, tzinfo=CET),
        steps=[
            RouteStep(
                instruction="U8 Richtung Hermannstraße",
                mode="TRANSIT",
                distance_meters=3200,
                duration_seconds=480,
                transit_line="U8",
                transit_stops=3,
            ),
            RouteStep(
                instruction="Fußweg zum Ausgang",
                mode="WALKING",
                distance_meters=120,
                duration_seconds=90,
            ),
        ],
        deep_links=DeepLinks(
            google_maps="https://maps.google.com/?saddr=Alexanderplatz&daddr=Kottbusser+Tor",
            apple_maps="https://maps.apple.com/?saddr=Alexanderplatz&daddr=Kottbusser+Tor",
        ),
    )


@pytest.fixture()
def route_no_links() -> RouteResult:
    return RouteResult(
        origin="A",
        destination="B",
        mode=TransportMode.WALKING,
        duration_seconds=600,
        departure=datetime(2026, 3, 25, 10, 0, tzinfo=CET),
        arrival=datetime(2026, 3, 25, 10, 10, tzinfo=CET),
        steps=[],
        deep_links=DeepLinks(google_maps="https://maps.google.com"),
    )


# ---------------------------------------------------------------------------
# print_route (Rich console output)
# ---------------------------------------------------------------------------

class TestPrintRoute:
    def test_no_exception(self, sample_route: RouteResult):
        """print_route should run without errors."""
        print_route(sample_route)

    def test_captures_origin_destination(self, sample_route: RouteResult, capsys):
        print_route(sample_route)
        out = capsys.readouterr().out
        assert "Alexanderplatz" in out
        assert "Kottbusser Tor" in out

    def test_shows_duration(self, sample_route: RouteResult, capsys):
        print_route(sample_route)
        out = capsys.readouterr().out
        assert "15 min" in out

    def test_shows_steps(self, sample_route: RouteResult, capsys):
        print_route(sample_route)
        out = capsys.readouterr().out
        assert "U8" in out
        assert "stops" in out

    def test_shows_deep_links(self, sample_route: RouteResult, capsys):
        print_route(sample_route)
        out = capsys.readouterr().out
        assert "Google Maps" in out
        assert "Apple Maps" in out

    def test_empty_steps(self, route_no_links: RouteResult, capsys):
        print_route(route_no_links)
        out = capsys.readouterr().out
        assert "A" in out
        assert "B" in out

    def test_departure_printed_in_local_tz(self, capsys):
        """Regression: UTC-aware datetimes must be converted to local tz before
        formatting Depart/Arrive (P0 bug: showed UTC wall clock)."""
        utc_dep = datetime(2026, 4, 18, 22, 26, tzinfo=timezone.utc)
        utc_arr = datetime(2026, 4, 18, 22, 46, tzinfo=timezone.utc)
        local_dep = utc_dep.astimezone().strftime("%H:%M")
        local_arr = utc_arr.astimezone().strftime("%H:%M")
        r = RouteResult(
            origin="X",
            destination="Y",
            mode=TransportMode.TRANSIT,
            duration_seconds=1200,
            departure=utc_dep,
            arrival=utc_arr,
            steps=[],
            deep_links=DeepLinks(google_maps="https://maps.google.com"),
        )
        print_route(r)
        out = capsys.readouterr().out
        assert f"Depart {local_dep}" in out
        assert f"Arrive {local_arr}" in out


# ---------------------------------------------------------------------------
# print_route_json (structured JSON for agents)
# ---------------------------------------------------------------------------

class TestPrintRouteJson:
    def test_returns_valid_json(self, sample_route: RouteResult):
        result = print_route_json(sample_route)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_contains_key_fields(self, sample_route: RouteResult):
        data = json.loads(print_route_json(sample_route))
        assert data["origin"] == "Alexanderplatz, Berlin"
        assert data["destination"] == "Kottbusser Tor, Berlin"
        assert data["duration_seconds"] == 900
        assert data["mode"] == "transit"

    def test_contains_steps(self, sample_route: RouteResult):
        data = json.loads(print_route_json(sample_route))
        assert len(data["steps"]) == 2
        assert data["steps"][0]["transit_line"] == "U8"

    def test_contains_deep_links(self, sample_route: RouteResult):
        data = json.loads(print_route_json(sample_route))
        assert "google_maps" in data["deep_links"]

    def test_contains_human_readable_duration(self, sample_route: RouteResult):
        data = json.loads(print_route_json(sample_route))
        assert data["duration_human"] == "15 min"
