"""CLI integration tests for kit."""

import json

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from kit.cli import app
from kit.route.core import DeepLinks, RouteResult, RouteStep, TransportMode

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_route_result(**overrides) -> RouteResult:
    """Build a RouteResult with sensible defaults for testing."""
    from datetime import datetime, timezone, timedelta

    defaults = dict(
        origin="Alexanderplatz, Berlin",
        destination="Brandenburger Tor, Berlin",
        mode=TransportMode.TRANSIT,
        duration_seconds=720,
        departure=datetime(2026, 3, 25, 18, 0, tzinfo=timezone(timedelta(hours=1))),
        arrival=datetime(2026, 3, 25, 18, 12, tzinfo=timezone(timedelta(hours=1))),
        steps=[
            RouteStep(
                instruction="U5 Richtung Hauptbahnhof",
                mode="transit",
                distance_meters=2400,
                duration_seconds=480,
                transit_line="U5",
                transit_stops=3,
            ),
            RouteStep(
                instruction="Walk to Brandenburger Tor",
                mode="walking",
                distance_meters=350,
                duration_seconds=240,
            ),
        ],
        deep_links=DeepLinks(
            google_maps="https://maps.google.com/?daddr=Brandenburger+Tor",
            apple_maps="https://maps.apple.com/?daddr=Brandenburger+Tor",
        ),
    )
    defaults.update(overrides)
    return RouteResult(**defaults)


# ---------------------------------------------------------------------------
# General CLI tests
# ---------------------------------------------------------------------------

def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    # Typer's no_args_is_help uses Click convention (exit code 0)
    # but some versions return 2; the key behavior is showing help text.
    assert "Usage" in result.output or "route" in result.output.lower()


# ---------------------------------------------------------------------------
# Route subcommand
# ---------------------------------------------------------------------------

def test_route_help():
    result = runner.invoke(app, ["route", "--help"])
    assert result.exit_code == 0
    assert "route" in result.output.lower()


@patch("kit.route.commands.plan_route")
def test_route_basic(mock_plan):
    mock_plan.return_value = _make_route_result()
    result = runner.invoke(app, ["route", "Alexanderplatz", "Brandenburger Tor"])
    assert result.exit_code == 0
    assert "Alexanderplatz" in result.output
    assert "Brandenburger Tor" in result.output
    mock_plan.assert_called_once()


@patch("kit.route.commands.plan_route")
def test_route_json_output(mock_plan):
    mock_plan.return_value = _make_route_result()
    result = runner.invoke(app, ["route", "A", "B", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["duration_seconds"] == 720
    assert data["origin"] == "Alexanderplatz, Berlin"
    assert "duration_human" in data


@patch("kit.route.commands.plan_route")
def test_route_mode_option(mock_plan):
    mock_plan.return_value = _make_route_result(mode=TransportMode.DRIVING)
    result = runner.invoke(app, ["route", "A", "B", "--mode", "driving"])
    assert result.exit_code == 0
    mock_plan.assert_called_once()
    call_kwargs = mock_plan.call_args
    # mode should be passed through
    assert call_kwargs.kwargs.get("mode") == TransportMode.DRIVING or \
           call_kwargs[1].get("mode") == TransportMode.DRIVING


@patch("kit.route.commands.plan_route")
def test_route_depart_option(mock_plan):
    mock_plan.return_value = _make_route_result()
    result = runner.invoke(app, ["route", "A", "B", "--depart", "18:30"])
    assert result.exit_code == 0
    mock_plan.assert_called_once()


@patch("kit.route.commands.plan_route")
def test_route_rich_output_contains_steps(mock_plan):
    mock_plan.return_value = _make_route_result()
    result = runner.invoke(app, ["route", "A", "B"])
    assert result.exit_code == 0
    assert "U5" in result.output
    assert "18:00" in result.output
    assert "18:12" in result.output


def test_route_depart_and_arrive_exclusive():
    result = runner.invoke(app, ["route", "A", "B", "--depart", "18:30", "--arrive", "19:00"])
    assert result.exit_code != 0


@patch("kit.route.commands.plan_route")
def test_route_error_handling(mock_plan):
    from kit.errors import ConfigError
    mock_plan.side_effect = ConfigError("Google Maps API key not configured")
    result = runner.invoke(app, ["route", "A", "B"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Multi-stop route
# ---------------------------------------------------------------------------

@patch("kit.route.commands.plan_multi_route")
def test_route_multi(mock_multi):
    mock_multi.return_value = [
        _make_route_result(origin="A", destination="B"),
        _make_route_result(origin="B", destination="C"),
    ]
    result = runner.invoke(app, ["route", "multi", "A", "B", "C"])
    assert result.exit_code == 0
    mock_multi.assert_called_once()


@patch("kit.route.commands.plan_multi_route")
def test_route_multi_json(mock_multi):
    mock_multi.return_value = [
        _make_route_result(origin="A", destination="B"),
        _make_route_result(origin="B", destination="C"),
    ]
    result = runner.invoke(app, ["route", "multi", "A", "B", "C", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["origin"] == "A"
    assert data[1]["origin"] == "B"


def test_route_multi_needs_two_stops():
    result = runner.invoke(app, ["route", "multi", "A"])
    assert result.exit_code != 0
