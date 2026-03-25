"""Tests for Google Maps Directions + Geocoding client."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from kit.route.google_maps import GoogleMapsRouter
from kit.route.core import RouteRequest, TransportMode
from kit.errors import RouteNotFoundError, GeocodingError, APIError


SAMPLE_DIRECTIONS_RESPONSE = {
    "status": "OK",
    "routes": [{
        "legs": [{
            "start_address": "Alexanderplatz, Berlin",
            "end_address": "Goerlitzer Park, Berlin",
            "duration": {"value": 1080, "text": "18 mins"},
            "distance": {"value": 4200, "text": "4.2 km"},
            "departure_time": {"value": 1711388400},
            "arrival_time": {"value": 1711389480},
            "steps": [
                {
                    "html_instructions": "U8 Richtung Hermannstr",
                    "travel_mode": "TRANSIT",
                    "duration": {"value": 420},
                    "distance": {"value": 2100},
                    "transit_details": {
                        "line": {"short_name": "U8"},
                        "num_stops": 3,
                    },
                },
                {
                    "html_instructions": "Walk to destination",
                    "travel_mode": "WALKING",
                    "duration": {"value": 240},
                    "distance": {"value": 350},
                },
            ],
        }],
    }],
}

SAMPLE_GEOCODE_RESPONSE = [
    {
        "geometry": {
            "location": {"lat": 52.5219, "lng": 13.4132},
        },
        "formatted_address": "Alexanderplatz, 10178 Berlin, Germany",
    }
]


@pytest.fixture
def mock_gmaps():
    with patch("kit.route.google_maps.googlemaps.Client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


# --- plan() tests ---


def test_plan_route_basic(mock_gmaps):
    """Basic route planning returns correct duration, steps and transit line."""
    mock_gmaps.directions.return_value = [SAMPLE_DIRECTIONS_RESPONSE["routes"][0]]
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="Alexanderplatz", destination="Goerlitzer Park")
    result = router.plan(req)
    assert result.duration_seconds == 1080
    assert len(result.steps) == 2
    assert result.steps[0].transit_line == "U8"
    assert result.steps[0].transit_stops == 3
    assert result.steps[1].mode == "walking"


def test_plan_route_populates_addresses(mock_gmaps):
    """Result uses start/end addresses from API response."""
    mock_gmaps.directions.return_value = [SAMPLE_DIRECTIONS_RESPONSE["routes"][0]]
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="Alexanderplatz", destination="Goerlitzer Park")
    result = router.plan(req)
    assert result.origin == "Alexanderplatz, Berlin"
    assert result.destination == "Goerlitzer Park, Berlin"


def test_plan_route_generates_deep_links(mock_gmaps):
    """Result includes deep links."""
    mock_gmaps.directions.return_value = [SAMPLE_DIRECTIONS_RESPONSE["routes"][0]]
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="Alexanderplatz", destination="Goerlitzer Park")
    result = router.plan(req)
    assert result.deep_links.google_maps.startswith("https://www.google.com/maps/dir/")


def test_plan_route_no_results(mock_gmaps):
    """Empty results raise RouteNotFoundError."""
    mock_gmaps.directions.return_value = []
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="Nowhere", destination="Nowhere2")
    with pytest.raises(RouteNotFoundError):
        router.plan(req)


def test_plan_route_with_departure(mock_gmaps):
    """Departure time is forwarded to the API."""
    mock_gmaps.directions.return_value = [SAMPLE_DIRECTIONS_RESPONSE["routes"][0]]
    router = GoogleMapsRouter(api_key="test-key")
    dt = datetime(2026, 3, 25, 18, 30, tzinfo=timezone(timedelta(hours=1)))
    req = RouteRequest(origin="A", destination="B", departure=dt)
    router.plan(req)
    call_kwargs = mock_gmaps.directions.call_args
    assert call_kwargs[1].get("departure_time") is not None


def test_plan_route_with_arrival(mock_gmaps):
    """Arrival time is forwarded to the API."""
    mock_gmaps.directions.return_value = [SAMPLE_DIRECTIONS_RESPONSE["routes"][0]]
    router = GoogleMapsRouter(api_key="test-key")
    dt = datetime(2026, 3, 25, 18, 30, tzinfo=timezone(timedelta(hours=1)))
    req = RouteRequest(origin="A", destination="B", arrival=dt)
    router.plan(req)
    call_kwargs = mock_gmaps.directions.call_args
    assert call_kwargs[1].get("arrival_time") is not None


def test_plan_route_api_error(mock_gmaps):
    """API exceptions are wrapped in APIError."""
    mock_gmaps.directions.side_effect = Exception("Network timeout")
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="A", destination="B")
    with pytest.raises(APIError, match="Network timeout"):
        router.plan(req)


def test_plan_route_driving_mode(mock_gmaps):
    """Driving mode is passed to the API correctly."""
    leg = {
        "start_address": "A",
        "end_address": "B",
        "duration": {"value": 600},
        "distance": {"value": 5000},
        "steps": [
            {
                "html_instructions": "Drive north",
                "travel_mode": "DRIVING",
                "duration": {"value": 600},
                "distance": {"value": 5000},
            },
        ],
    }
    mock_gmaps.directions.return_value = [{"legs": [leg]}]
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="A", destination="B", mode=TransportMode.DRIVING)
    result = router.plan(req)
    call_kwargs = mock_gmaps.directions.call_args[1]
    assert call_kwargs["mode"] == "driving"
    assert result.mode == TransportMode.DRIVING


# --- geocode() tests ---


def test_geocode_returns_lat_lng(mock_gmaps):
    """Geocode returns (lat, lng) tuple."""
    mock_gmaps.geocode.return_value = SAMPLE_GEOCODE_RESPONSE
    router = GoogleMapsRouter(api_key="test-key")
    lat, lng = router.geocode("Alexanderplatz, Berlin")
    assert abs(lat - 52.5219) < 0.001
    assert abs(lng - 13.4132) < 0.001


def test_geocode_no_results(mock_gmaps):
    """Empty geocode results raise GeocodingError."""
    mock_gmaps.geocode.return_value = []
    router = GoogleMapsRouter(api_key="test-key")
    with pytest.raises(GeocodingError):
        router.geocode("xyznonexistent12345")


def test_geocode_api_error(mock_gmaps):
    """Geocode API exceptions are wrapped in APIError."""
    mock_gmaps.geocode.side_effect = Exception("Auth failed")
    router = GoogleMapsRouter(api_key="test-key")
    with pytest.raises(APIError, match="Auth failed"):
        router.geocode("Berlin")
