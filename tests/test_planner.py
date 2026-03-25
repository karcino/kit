"""Tests for the high-level route planning API."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from kit.route.planner import plan_route, plan_multi_route
from kit.route.core import RouteRequest, RouteResult, RouteStep, TransportMode, DeepLinks
from kit.config import KitConfig


@pytest.fixture
def mock_router():
    with patch("kit.route.planner._get_router") as mock:
        router = MagicMock()
        mock.return_value = router
        yield router


@pytest.fixture
def sample_result():
    return RouteResult(
        origin="A",
        destination="B",
        mode=TransportMode.TRANSIT,
        duration_seconds=600,
        departure=datetime(2026, 3, 25, 18, 0, tzinfo=timezone(timedelta(hours=1))),
        arrival=datetime(2026, 3, 25, 18, 10, tzinfo=timezone(timedelta(hours=1))),
        steps=[],
        deep_links=DeepLinks(google_maps="https://maps.google.com"),
    )


def test_plan_route_string_args(mock_router, sample_result):
    """plan_route('A', 'B') resolves locations and returns a RouteResult."""
    mock_router.plan.return_value = sample_result
    result = plan_route("A", "B")
    assert result.duration_seconds == 600
    mock_router.plan.assert_called_once()


def test_plan_route_request_object(mock_router, sample_result):
    """plan_route(RouteRequest(...)) passes through to router."""
    mock_router.plan.return_value = sample_result
    req = RouteRequest(origin="A", destination="B", mode=TransportMode.WALKING)
    result = plan_route(req)
    assert result.duration_seconds == 600
    mock_router.plan.assert_called_once()


def test_plan_route_request_preserves_mode(mock_router, sample_result):
    """When passing a RouteRequest, its mode is forwarded unchanged."""
    mock_router.plan.return_value = sample_result
    req = RouteRequest(origin="A", destination="B", mode=TransportMode.WALKING)
    plan_route(req)
    call_args = mock_router.plan.call_args
    passed_request = call_args[0][0]
    assert passed_request.mode == TransportMode.WALKING


def test_plan_route_string_with_mode(mock_router, sample_result):
    """plan_route('A', 'B', mode=DRIVING) creates request with correct mode."""
    mock_router.plan.return_value = sample_result
    result = plan_route("A", "B", mode=TransportMode.DRIVING)
    assert result.duration_seconds == 600
    call_args = mock_router.plan.call_args
    passed_request = call_args[0][0]
    assert passed_request.mode == TransportMode.DRIVING


def test_plan_multi_route(mock_router, sample_result):
    """plan_multi_route(['A','B','C']) plans two sequential legs."""
    mock_router.plan.return_value = sample_result
    results = plan_multi_route(["A", "B", "C"])
    assert len(results) == 2  # A->B, B->C
    assert mock_router.plan.call_count == 2


def test_plan_multi_route_single_leg(mock_router, sample_result):
    """plan_multi_route with two stops yields a single leg."""
    mock_router.plan.return_value = sample_result
    results = plan_multi_route(["A", "B"])
    assert len(results) == 1
    assert mock_router.plan.call_count == 1


def test_plan_multi_route_no_stops():
    """plan_multi_route with fewer than 2 stops raises ValueError."""
    with pytest.raises(ValueError, match="at least 2 stops"):
        plan_multi_route(["A"])


def test_plan_multi_route_empty():
    """plan_multi_route with empty list raises ValueError."""
    with pytest.raises(ValueError, match="at least 2 stops"):
        plan_multi_route([])
