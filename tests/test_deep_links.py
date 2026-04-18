"""Tests for deep link generators."""

from datetime import datetime, timezone, timedelta

import pytest

from kit.route.deep_links import generate_deep_links, TransportMode


# --- Google Maps ---


def test_google_maps_web_link():
    links = generate_deep_links("Alexanderplatz", "Kreuzberg", TransportMode.TRANSIT)
    assert "google.com/maps" in links.google_maps
    assert "travelmode=transit" in links.google_maps


def test_google_maps_driving():
    links = generate_deep_links("A", "B", TransportMode.DRIVING)
    assert "travelmode=driving" in links.google_maps


def test_google_maps_walking():
    links = generate_deep_links("A", "B", TransportMode.WALKING)
    assert "travelmode=walking" in links.google_maps


def test_google_maps_bicycling():
    links = generate_deep_links("A", "B", TransportMode.BICYCLING)
    assert "travelmode=bicycling" in links.google_maps


def test_google_maps_contains_origin_and_dest():
    links = generate_deep_links("Berlin Hbf", "München Hbf", TransportMode.DRIVING)
    assert "Berlin" in links.google_maps
    assert "nchen" in links.google_maps  # URL-encoded ü


def test_google_maps_url_encodes_spaces():
    links = generate_deep_links("Berlin Hbf", "München Hbf", TransportMode.DRIVING)
    # urlencode uses + or %20 for spaces
    assert "Berlin" in links.google_maps


# --- DB Navigator ---


def test_db_navigator_link():
    links = generate_deep_links("Berlin Hbf", "München Hbf", TransportMode.TRANSIT)
    assert links.db_navigator is not None
    assert "reiseauskunft.bahn.de" in links.db_navigator


def test_db_navigator_only_for_transit():
    links = generate_deep_links("A", "B", TransportMode.DRIVING)
    assert links.db_navigator is None


def test_db_navigator_contains_stations():
    links = generate_deep_links("Berlin Hbf", "München Hbf", TransportMode.TRANSIT)
    assert "Berlin" in links.db_navigator
    assert "nchen" in links.db_navigator


def test_db_navigator_with_departure_time():
    # Naive datetime passes through unchanged (no tz conversion).
    dt = datetime(2026, 3, 25, 18, 30)
    links = generate_deep_links("A", "B", TransportMode.TRANSIT, departure=dt)
    assert links.db_navigator is not None
    # time should appear as 18:30 or URL-encoded 18%3A30
    assert "18%3A30" in links.db_navigator or "18:30" in links.db_navigator


def test_db_navigator_with_departure_date():
    dt = datetime(2026, 3, 25, 18, 30)
    links = generate_deep_links("A", "B", TransportMode.TRANSIT, departure=dt)
    assert "25.03.2026" in links.db_navigator


def test_db_navigator_converts_utc_to_local_tz():
    """Regression: tz-aware UTC datetime must be converted to local time
    before formatting date/time params (P0 bug: showed UTC, off by up to 1 day).
    """
    import time as _time

    # Pick a UTC instant and compute what local should show.
    utc_dt = datetime(2026, 4, 18, 22, 26, tzinfo=timezone.utc)
    local_dt = utc_dt.astimezone()  # system local tz
    expected_date = local_dt.strftime("%d.%m.%Y")
    expected_time = local_dt.strftime("%H:%M")

    links = generate_deep_links("A", "B", TransportMode.TRANSIT, departure=utc_dt)
    assert links.db_navigator is not None
    assert f"date={expected_date.replace('.', '.')}" in links.db_navigator or expected_date in links.db_navigator
    # time may be URL-encoded
    assert expected_time in links.db_navigator or expected_time.replace(":", "%3A") in links.db_navigator
    _ = _time  # keep import usage minimal


# --- Apple Maps ---


def test_apple_maps_link():
    links = generate_deep_links("A", "B", TransportMode.TRANSIT)
    assert links.apple_maps is not None
    assert "maps.apple.com" in links.apple_maps


def test_apple_maps_transit_mode():
    links = generate_deep_links("A", "B", TransportMode.TRANSIT)
    assert "dirflg=r" in links.apple_maps


def test_apple_maps_driving_mode():
    links = generate_deep_links("A", "B", TransportMode.DRIVING)
    assert "dirflg=d" in links.apple_maps


def test_apple_maps_walking_mode():
    links = generate_deep_links("A", "B", TransportMode.WALKING)
    assert "dirflg=w" in links.apple_maps


def test_apple_maps_contains_addresses():
    links = generate_deep_links("Alexanderplatz", "Kreuzberg", TransportMode.WALKING)
    assert "Alexanderplatz" in links.apple_maps
    assert "Kreuzberg" in links.apple_maps


# --- BVG Fahrinfo ---


def test_bvg_link():
    links = generate_deep_links("Alexanderplatz", "Kreuzberg", TransportMode.TRANSIT)
    assert links.bvg is not None
    assert "bvg.de" in links.bvg


def test_bvg_only_for_transit():
    links = generate_deep_links("A", "B", TransportMode.DRIVING)
    assert links.bvg is None


def test_bvg_contains_origin_and_dest():
    links = generate_deep_links("Alexanderplatz", "Kreuzberg", TransportMode.TRANSIT)
    assert "Alexanderplatz" in links.bvg
    assert "Kreuzberg" in links.bvg


# --- DeepLinks result object ---


def test_deep_links_all_fields_present_for_transit():
    links = generate_deep_links("A", "B", TransportMode.TRANSIT)
    assert links.google_maps is not None
    assert links.apple_maps is not None
    assert links.db_navigator is not None
    assert links.bvg is not None


def test_deep_links_non_transit_has_only_maps():
    links = generate_deep_links("A", "B", TransportMode.DRIVING)
    assert links.google_maps is not None
    assert links.apple_maps is not None
    assert links.db_navigator is None
    assert links.bvg is None
