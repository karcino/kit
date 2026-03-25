# tests/test_geo.py
import pytest
from kit.utils.geo import parse_location, LocationType


def test_parse_coordinates():
    loc = parse_location("52.5200,13.4050")
    assert loc.type == LocationType.COORDINATES
    assert loc.lat == pytest.approx(52.52)
    assert loc.lng == pytest.approx(13.405)


def test_parse_coordinates_with_space():
    loc = parse_location("52.5200, 13.4050")
    assert loc.type == LocationType.COORDINATES


def test_parse_named_location_home():
    loc = parse_location("home")
    assert loc.type == LocationType.SAVED
    assert loc.name == "home"


def test_parse_address():
    loc = parse_location("Alexanderplatz, Berlin")
    assert loc.type == LocationType.ADDRESS
    assert loc.raw == "Alexanderplatz, Berlin"


def test_parse_negative_coordinates():
    loc = parse_location("-33.8688,151.2093")
    assert loc.type == LocationType.COORDINATES
    assert loc.lat == pytest.approx(-33.8688)


def test_resolve_saved_location():
    from kit.config import KitConfig
    config = KitConfig(home="Teststr 1, 10999 Berlin")
    loc = parse_location("home")
    resolved = loc.resolve(config)
    assert resolved == "Teststr 1, 10999 Berlin"


def test_resolve_coordinates():
    loc = parse_location("52.52,13.405")
    resolved = loc.resolve()
    assert resolved == "52.52,13.405"


def test_resolve_address():
    loc = parse_location("Alexanderplatz")
    resolved = loc.resolve()
    assert resolved == "Alexanderplatz"


def test_resolve_saved_without_config_raises():
    loc = parse_location("home")
    with pytest.raises(ValueError, match="Config required"):
        loc.resolve()


def test_resolve_saved_not_configured_raises():
    from kit.config import KitConfig
    config = KitConfig(home=None)
    loc = parse_location("home")
    with pytest.raises(ValueError, match="not configured"):
        loc.resolve(config)


def test_parse_whitespace_stripped():
    loc = parse_location("  52.52, 13.405  ")
    assert loc.type == LocationType.COORDINATES


def test_parse_home_case_insensitive():
    loc = parse_location("Home")
    assert loc.type == LocationType.SAVED
    assert loc.name == "home"


def test_parse_integer_coordinates():
    loc = parse_location("52,13")
    assert loc.type == LocationType.COORDINATES
    assert loc.lat == pytest.approx(52.0)
    assert loc.lng == pytest.approx(13.0)
