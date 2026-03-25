# tests/test_route_core.py
import pytest
from datetime import datetime, timezone, timedelta
from kit.route.core import RouteRequest, RouteResult, RouteStep, DeepLinks, TransportMode


def test_route_request_defaults():
    req = RouteRequest(origin="A", destination="B")
    assert req.mode == TransportMode.TRANSIT
    assert req.departure is None
    assert req.arrival is None


def test_route_request_mutually_exclusive():
    with pytest.raises(ValueError, match="mutually exclusive"):
        RouteRequest(
            origin="A", destination="B",
            departure=datetime.now(tz=timezone.utc),
            arrival=datetime.now(tz=timezone.utc),
        )


def test_route_request_with_departure():
    dt = datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc)
    req = RouteRequest(origin="A", destination="B", departure=dt)
    assert req.departure == dt
    assert req.arrival is None


def test_route_request_with_arrival():
    dt = datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc)
    req = RouteRequest(origin="A", destination="B", arrival=dt)
    assert req.arrival == dt
    assert req.departure is None


def test_route_request_modes():
    for mode in TransportMode:
        req = RouteRequest(origin="A", destination="B", mode=mode)
        assert req.mode == mode


def test_route_request_alternatives_default():
    req = RouteRequest(origin="A", destination="B")
    assert req.alternatives == 1


def test_route_result_duration_human():
    result = RouteResult(
        origin="A", destination="B",
        mode=TransportMode.TRANSIT,
        duration_seconds=1080,
        departure=datetime(2026, 3, 25, 18, 30, tzinfo=timezone(timedelta(hours=1))),
        arrival=datetime(2026, 3, 25, 18, 48, tzinfo=timezone(timedelta(hours=1))),
        steps=[],
        deep_links=DeepLinks(google_maps="", db_navigator=None, apple_maps=None, bvg=None),
    )
    assert result.duration_human == "18 min"


def test_route_result_duration_human_hours():
    result = RouteResult(
        origin="A", destination="B",
        mode=TransportMode.TRANSIT,
        duration_seconds=5400,
        departure=datetime(2026, 3, 25, 18, 0, tzinfo=timezone(timedelta(hours=1))),
        arrival=datetime(2026, 3, 25, 19, 30, tzinfo=timezone(timedelta(hours=1))),
        steps=[],
        deep_links=DeepLinks(google_maps=""),
    )
    assert result.duration_human == "1h 30min"


def test_route_result_duration_human_exact_hour():
    result = RouteResult(
        origin="A", destination="B",
        mode=TransportMode.TRANSIT,
        duration_seconds=3600,
        departure=datetime(2026, 3, 25, 18, 0, tzinfo=timezone(timedelta(hours=1))),
        arrival=datetime(2026, 3, 25, 19, 0, tzinfo=timezone(timedelta(hours=1))),
        steps=[],
        deep_links=DeepLinks(google_maps=""),
    )
    assert result.duration_human == "1h 0min"


def test_route_step():
    step = RouteStep(
        instruction="U8 Richtung Hermannstr",
        mode="transit",
        distance_meters=2100,
        duration_seconds=420,
        transit_line="U8",
        transit_stops=3,
    )
    assert step.duration_human == "7 min"


def test_route_step_no_transit():
    step = RouteStep(
        instruction="Walk to Alexanderplatz",
        mode="walking",
        distance_meters=500,
        duration_seconds=360,
    )
    assert step.transit_line is None
    assert step.transit_stops is None
    assert step.duration_human == "6 min"


def test_transport_mode_values():
    assert TransportMode.TRANSIT.value == "transit"
    assert TransportMode.WALKING.value == "walking"
    assert TransportMode.BICYCLING.value == "bicycling"
    assert TransportMode.DRIVING.value == "driving"


def test_deep_links_defaults():
    dl = DeepLinks(google_maps="https://maps.google.com/test")
    assert dl.google_maps == "https://maps.google.com/test"
    assert dl.db_navigator is None
    assert dl.apple_maps is None
    assert dl.bvg is None


def test_deep_links_all_filled():
    dl = DeepLinks(
        google_maps="https://maps.google.com",
        db_navigator="https://db.de",
        apple_maps="https://maps.apple.com",
        bvg="https://bvg.de",
    )
    assert dl.db_navigator == "https://db.de"
    assert dl.apple_maps == "https://maps.apple.com"
    assert dl.bvg == "https://bvg.de"
