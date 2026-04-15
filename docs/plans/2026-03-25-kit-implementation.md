# Kit Toolbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an agentic-ready personal CLI toolbox with route planning, calendar integration, and MCP Server — three interfaces (CLI, Python API, MCP) sharing one core.

**Architecture:** Monorepo Python package with Typer CLI + MCP Server entry-points. Core logic in `src/kit/route/` and `src/kit/cal/`. Google Maps Directions API for routing, Google Calendar API for events. Pydantic models for all data, Rich for CLI output. TDD throughout.

**Tech Stack:** Python 3.11+, Typer, Pydantic, Rich, googlemaps, google-api-python-client, google-auth, mcp (Python SDK), pytest, pytest-vcr, dateparser

**Spec:** `docs/specs/2026-03-25-kit-toolbox-design.md`

---

## File Structure

```
src/kit/
├── __init__.py              # Package version
├── cli.py                   # Typer app with subcommand routing
├── config.py                # TOML config load/save/setup
├── mcp_server.py            # MCP Server entry-point
├── route/
│   ├── __init__.py          # Public API re-exports
│   ├── core.py              # RouteRequest, RouteResult, RouteStep (Pydantic)
│   ├── google_maps.py       # Google Maps Directions + Geocoding client
│   ├── deep_links.py        # URL generators for GMaps, DB Nav, Apple Maps, BVG
│   ├── planner.py           # plan_multi_route(), plan_day()
│   ├── commands.py          # Typer subcommands for "kit route"
│   └── mcp_tools.py         # MCP tool registrations for route
├── cal/
│   ├── __init__.py          # Public API re-exports
│   ├── core.py              # CalendarEvent, TravelBuffer (Pydantic)
│   ├── google_cal.py        # Google Calendar API client
│   ├── commands.py          # Typer subcommands for "kit cal"
│   └── mcp_tools.py         # MCP tool registrations for cal
└── utils/
    ├── __init__.py
    ├── geo.py               # Coordinate parsing, location resolution
    └── formatting.py        # Human-readable duration, tables, Rich output

tests/
├── conftest.py              # Shared fixtures, sample API responses
├── test_geo.py              # Coordinate parsing, location resolution
├── test_config.py           # Config load/save/defaults
├── test_route_core.py       # RouteRequest/RouteResult models
├── test_deep_links.py       # Deep link URL generation
├── test_google_maps.py      # Google Maps client (VCR cassettes)
├── test_planner.py          # Multi-route, day planning
├── test_cal_core.py         # CalendarEvent models
├── test_google_cal.py       # Google Calendar client (VCR)
├── test_cli.py              # CLI integration tests
└── test_mcp_server.py       # MCP tool tests

cassettes/                   # VCR recorded API responses
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/kit/__init__.py`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "kit"
version = "0.1.0"
description = "Agentic-ready personal CLI toolbox with MCP Server"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [{ name = "Paul Fiedler" }]
dependencies = [
    "typer[all]>=0.9",
    "pydantic>=2.0",
    "rich>=13.0",
    "googlemaps>=4.10",
    "google-api-python-client>=2.0",
    "google-auth-oauthlib>=1.0",
    "google-auth>=2.0",
    "mcp>=1.0",
    "dateparser>=1.2",
    "tomli-w>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-vcr>=6.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "mypy>=1.10",
]

[project.scripts]
kit = "kit.cli:app"
kit-mcp = "kit.mcp_server:run"

[tool.hatch.build.targets.wheel]
packages = ["src/kit"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["smoke: real API calls (deselect with '-m not smoke')"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
```

- [ ] **Step 2: Create src/kit/__init__.py**

```python
"""Kit — Agentic-ready personal CLI toolbox."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.egg-info/
dist/
build/
.venv/
*.pyc
.mypy_cache/
.pytest_cache/
.ruff_cache/
cassettes/
~/.config/kit/
```

- [ ] **Step 4: Create LICENSE (MIT)**

- [ ] **Step 5: Create empty tests/conftest.py**

```python
"""Shared test fixtures for kit."""
```

- [ ] **Step 6: Install in dev mode and verify**

Run: `cd /Users/p.fiedler/Desktop/Code_Projects/kit && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
Expected: Clean install, `kit --help` shows Typer default

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/ LICENSE .gitignore
git commit -m "feat: project scaffolding with pyproject.toml and dev dependencies"
```

---

## Task 2: Config System

**Files:**
- Create: `src/kit/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config**

```python
# tests/test_config.py
import pytest
from pathlib import Path
from kit.config import KitConfig, load_config, save_config, get_config_dir


def test_get_config_dir_returns_path():
    path = get_config_dir()
    assert isinstance(path, Path)
    assert path.name == "kit"


def test_default_config():
    config = KitConfig()
    assert config.default_mode == "transit"
    assert config.home is None
    assert config.google_maps_api_key is None
    assert config.calendar_id == "primary"
    assert config.meta_version == 1


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("KIT_GOOGLE_MAPS_API_KEY", "test-key-123")
    config = KitConfig()
    assert config.google_maps_api_key == "test-key-123"


def test_save_and_load_config(tmp_path):
    config = KitConfig(home="Teststr 1, Berlin", default_mode="bicycling")
    save_config(config, config_dir=tmp_path)
    loaded = load_config(config_dir=tmp_path)
    assert loaded.home == "Teststr 1, Berlin"
    assert loaded.default_mode == "bicycling"


def test_load_config_missing_file_returns_default(tmp_path):
    config = load_config(config_dir=tmp_path)
    assert config.default_mode == "transit"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement config.py**

```python
# src/kit/config.py
"""Config management for kit. Stores settings in ~/.config/kit/config.toml."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w


def get_config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kit"


class KitConfig(BaseModel):
    meta_version: int = 1
    default_mode: str = "transit"
    home: str | None = None
    google_maps_api_key: str | None = Field(
        default_factory=lambda: os.environ.get("KIT_GOOGLE_MAPS_API_KEY")
    )
    calendar_id: str = "primary"


def load_config(config_dir: Path | None = None) -> KitConfig:
    config_dir = config_dir or get_config_dir()
    config_file = config_dir / "config.toml"
    if not config_file.exists():
        return KitConfig()
    data = tomllib.loads(config_file.read_text())
    flat = {}
    for section in data.values():
        if isinstance(section, dict):
            flat.update(section)
        else:
            flat.update(data)
            break
    return KitConfig(**flat)


def save_config(config: KitConfig, config_dir: Path | None = None) -> None:
    config_dir = config_dir or get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"
    data = {
        "meta": {"version": config.meta_version},
        "general": {"default_mode": config.default_mode},
        "google_maps": {},
        "google_calendar": {"calendar_id": config.calendar_id},
    }
    if config.home:
        data["general"]["home"] = config.home
    if config.google_maps_api_key:
        data["google_maps"]["api_key"] = config.google_maps_api_key
    config_file.write_text(tomli_w.dumps(data))
    config_file.chmod(0o600)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/kit/config.py tests/test_config.py
git commit -m "feat: config system with TOML storage and env var fallback"
```

---

## Task 3: Geo Utilities

**Files:**
- Create: `src/kit/utils/__init__.py`
- Create: `src/kit/utils/geo.py`
- Create: `tests/test_geo.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/test_geo.py -v`

- [ ] **Step 3: Implement geo.py**

```python
# src/kit/utils/__init__.py
# (empty)

# src/kit/utils/geo.py
"""Location parsing and resolution utilities."""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from kit.config import KitConfig

_COORD_PATTERN = re.compile(
    r"^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$"
)
_SAVED_NAMES = {"home"}


class LocationType(Enum):
    COORDINATES = "coordinates"
    ADDRESS = "address"
    SAVED = "saved"


class ParsedLocation(BaseModel):
    raw: str
    type: LocationType
    lat: float | None = None
    lng: float | None = None
    name: str | None = None

    def resolve(self, config: KitConfig | None = None) -> str:
        if self.type == LocationType.COORDINATES:
            return f"{self.lat},{self.lng}"
        if self.type == LocationType.SAVED:
            if config is None:
                raise ValueError(f"Config required to resolve saved location '{self.name}'")
            value = getattr(config, self.name, None)  # type: ignore[arg-type]
            if not value:
                raise ValueError(f"Saved location '{self.name}' not configured. Run: kit setup")
            return value
        return self.raw


def parse_location(raw: str) -> ParsedLocation:
    raw = raw.strip()
    match = _COORD_PATTERN.match(raw)
    if match:
        return ParsedLocation(
            raw=raw,
            type=LocationType.COORDINATES,
            lat=float(match.group(1)),
            lng=float(match.group(2)),
        )
    if raw.lower() in _SAVED_NAMES:
        return ParsedLocation(raw=raw, type=LocationType.SAVED, name=raw.lower())
    return ParsedLocation(raw=raw, type=LocationType.ADDRESS)
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_geo.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/kit/utils/ tests/test_geo.py
git commit -m "feat: geo utilities for coordinate parsing and location resolution"
```

---

## Task 4: Route Core Models

**Files:**
- Create: `src/kit/route/__init__.py`
- Create: `src/kit/route/core.py`
- Create: `tests/test_route_core.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — expect fail**

- [ ] **Step 3: Implement core.py**

```python
# src/kit/route/__init__.py
from kit.route.core import RouteRequest, RouteResult, RouteStep, TransportMode, DeepLinks

__all__ = ["RouteRequest", "RouteResult", "RouteStep", "TransportMode", "DeepLinks"]

# src/kit/route/core.py
"""Core data models for route planning."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator


class TransportMode(str, Enum):
    TRANSIT = "transit"
    WALKING = "walking"
    BICYCLING = "bicycling"
    DRIVING = "driving"


class DeepLinks(BaseModel):
    google_maps: str
    db_navigator: str | None = None
    apple_maps: str | None = None
    bvg: str | None = None


class RouteStep(BaseModel):
    instruction: str
    mode: str
    distance_meters: int
    duration_seconds: int
    transit_line: str | None = None
    transit_stops: int | None = None

    @property
    def duration_human(self) -> str:
        return _format_duration(self.duration_seconds)


class RouteRequest(BaseModel):
    origin: str
    destination: str
    mode: TransportMode = TransportMode.TRANSIT
    departure: datetime | None = None
    arrival: datetime | None = None
    alternatives: int = 1

    @model_validator(mode="after")
    def check_times_exclusive(self) -> RouteRequest:
        if self.departure and self.arrival:
            raise ValueError("departure and arrival are mutually exclusive")
        return self


class RouteResult(BaseModel):
    origin: str
    destination: str
    mode: TransportMode
    duration_seconds: int
    departure: datetime
    arrival: datetime
    steps: list[RouteStep]
    deep_links: DeepLinks

    @property
    def duration_human(self) -> str:
        return _format_duration(self.duration_seconds)


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes}min"
    return f"{minutes} min"
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_route_core.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/kit/route/ tests/test_route_core.py
git commit -m "feat: route core models with Pydantic validation"
```

---

## Task 5: Deep Link Generation

**Files:**
- Create: `src/kit/route/deep_links.py`
- Create: `tests/test_deep_links.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_deep_links.py
from kit.route.deep_links import generate_deep_links
from kit.route.core import TransportMode


def test_google_maps_web_link():
    links = generate_deep_links("Alexanderplatz", "Kreuzberg", TransportMode.TRANSIT)
    assert "maps.google.com" in links.google_maps or "google.com/maps" in links.google_maps
    assert "travelmode=transit" in links.google_maps


def test_google_maps_driving():
    links = generate_deep_links("A", "B", TransportMode.DRIVING)
    assert "travelmode=driving" in links.google_maps


def test_db_navigator_link():
    links = generate_deep_links("Berlin Hbf", "München Hbf", TransportMode.TRANSIT)
    assert links.db_navigator is not None
    assert "reiseauskunft.bahn.de" in links.db_navigator


def test_db_navigator_only_for_transit():
    links = generate_deep_links("A", "B", TransportMode.DRIVING)
    assert links.db_navigator is None


def test_apple_maps_link():
    links = generate_deep_links("A", "B", TransportMode.TRANSIT)
    assert links.apple_maps is not None
    assert "maps.apple.com" in links.apple_maps


def test_deep_links_with_departure_time():
    from datetime import datetime, timezone, timedelta
    dt = datetime(2026, 3, 25, 18, 30, tzinfo=timezone(timedelta(hours=1)))
    links = generate_deep_links("A", "B", TransportMode.TRANSIT, departure=dt)
    assert links.db_navigator is not None
    assert "time=18%3A30" in links.db_navigator or "time=18:30" in links.db_navigator
```

- [ ] **Step 2: Run tests — expect fail**

- [ ] **Step 3: Implement deep_links.py**

```python
# src/kit/route/deep_links.py
"""Deep link generators for navigation apps."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote, urlencode

from kit.route.core import DeepLinks, TransportMode

_MODE_MAP_GMAPS = {
    TransportMode.TRANSIT: "transit",
    TransportMode.WALKING: "walking",
    TransportMode.BICYCLING: "bicycling",
    TransportMode.DRIVING: "driving",
}

_MODE_MAP_APPLE = {
    TransportMode.TRANSIT: "r",
    TransportMode.WALKING: "w",
    TransportMode.DRIVING: "d",
    TransportMode.BICYCLING: "w",  # Apple Maps has no bike mode
}


def generate_deep_links(
    origin: str,
    destination: str,
    mode: TransportMode,
    departure: datetime | None = None,
) -> DeepLinks:
    google_maps = _google_maps_link(origin, destination, mode)
    apple_maps = _apple_maps_link(origin, destination, mode)
    db_navigator = _db_navigator_link(origin, destination, departure) if mode == TransportMode.TRANSIT else None
    bvg = _bvg_link(origin, destination) if mode == TransportMode.TRANSIT else None

    return DeepLinks(
        google_maps=google_maps,
        db_navigator=db_navigator,
        apple_maps=apple_maps,
        bvg=bvg,
    )


def _google_maps_link(origin: str, destination: str, mode: TransportMode) -> str:
    params = {
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": _MODE_MAP_GMAPS[mode],
    }
    return f"https://www.google.com/maps/dir/?{urlencode(params)}"


def _apple_maps_link(origin: str, destination: str, mode: TransportMode) -> str:
    params = {
        "saddr": origin,
        "daddr": destination,
        "dirflg": _MODE_MAP_APPLE[mode],
    }
    return f"https://maps.apple.com/?{urlencode(params)}"


def _db_navigator_link(
    origin: str, destination: str, departure: datetime | None = None,
) -> str:
    params: dict[str, str] = {"S": origin, "Z": destination}
    if departure:
        params["date"] = departure.strftime("%d.%m.%Y")
        params["time"] = departure.strftime("%H:%M")
    return f"https://reiseauskunft.bahn.de/bin/query.exe/dn?{urlencode(params)}"


def _bvg_link(origin: str, destination: str) -> str:
    params = {"from": origin, "to": destination}
    return f"https://fahrinfo.bvg.de/Fahrinfo/bin/query.bin/dn?{urlencode(params)}"
```

- [ ] **Step 4: Run tests — expect pass**

- [ ] **Step 5: Commit**

```bash
git add src/kit/route/deep_links.py tests/test_deep_links.py
git commit -m "feat: deep link generation for Google Maps, DB Navigator, Apple Maps, BVG"
```

---

## Task 6: Google Maps Client

**Files:**
- Create: `src/kit/route/google_maps.py`
- Create: `tests/test_google_maps.py`
- Create: `src/kit/errors.py`

- [ ] **Step 1: Create error hierarchy**

```python
# src/kit/errors.py
"""Custom exceptions for kit."""


class KitError(Exception):
    """Base exception for all kit errors."""


class ConfigError(KitError):
    """Missing or invalid configuration."""


class RouteNotFoundError(KitError):
    """No route found between locations."""


class GeocodingError(KitError):
    """Could not geocode address."""


class APIError(KitError):
    """External API error (rate limit, auth, network)."""


class CalendarError(KitError):
    """Calendar API error."""
```

- [ ] **Step 2: Write failing tests for Google Maps client**

```python
# tests/test_google_maps.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from kit.route.google_maps import GoogleMapsRouter
from kit.route.core import RouteRequest, TransportMode
from kit.errors import RouteNotFoundError, APIError

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


@pytest.fixture
def mock_gmaps():
    with patch("kit.route.google_maps.googlemaps.Client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_plan_route_basic(mock_gmaps):
    mock_gmaps.directions.return_value = [SAMPLE_DIRECTIONS_RESPONSE["routes"][0]]
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="Alexanderplatz", destination="Goerlitzer Park")
    result = router.plan(req)
    assert result.duration_seconds == 1080
    assert len(result.steps) == 2
    assert result.steps[0].transit_line == "U8"


def test_plan_route_no_results(mock_gmaps):
    mock_gmaps.directions.return_value = []
    router = GoogleMapsRouter(api_key="test-key")
    req = RouteRequest(origin="Nowhere", destination="Nowhere2")
    with pytest.raises(RouteNotFoundError):
        router.plan(req)


def test_plan_route_with_departure(mock_gmaps):
    mock_gmaps.directions.return_value = [SAMPLE_DIRECTIONS_RESPONSE["routes"][0]]
    router = GoogleMapsRouter(api_key="test-key")
    dt = datetime(2026, 3, 25, 18, 30, tzinfo=timezone(timedelta(hours=1)))
    req = RouteRequest(origin="A", destination="B", departure=dt)
    router.plan(req)
    call_kwargs = mock_gmaps.directions.call_args
    assert call_kwargs[1].get("departure_time") is not None
```

- [ ] **Step 3: Implement google_maps.py**

```python
# src/kit/route/google_maps.py
"""Google Maps Directions API client."""

from __future__ import annotations

from datetime import datetime, timezone

import googlemaps

from kit.errors import APIError, RouteNotFoundError
from kit.route.core import DeepLinks, RouteRequest, RouteResult, RouteStep
from kit.route.deep_links import generate_deep_links


class GoogleMapsRouter:
    def __init__(self, api_key: str) -> None:
        self._client = googlemaps.Client(key=api_key)

    def plan(self, request: RouteRequest) -> RouteResult:
        kwargs: dict = {
            "origin": request.origin,
            "destination": request.destination,
            "mode": request.mode.value,
            "alternatives": request.alternatives > 1,
        }
        if request.departure:
            kwargs["departure_time"] = request.departure
        if request.arrival:
            kwargs["arrival_time"] = request.arrival

        try:
            results = self._client.directions(**kwargs)
        except Exception as e:
            raise APIError(f"Google Maps API error: {e}") from e

        if not results:
            raise RouteNotFoundError(
                f"No route found from '{request.origin}' to '{request.destination}' "
                f"via {request.mode.value}"
            )

        route = results[0]
        leg = route["legs"][0]

        steps = [_parse_step(s) for s in leg.get("steps", [])]

        dep_time = leg.get("departure_time", {}).get("value")
        arr_time = leg.get("arrival_time", {}).get("value")
        departure = datetime.fromtimestamp(dep_time, tz=timezone.utc) if dep_time else request.departure or datetime.now(tz=timezone.utc)
        arrival_dt = datetime.fromtimestamp(arr_time, tz=timezone.utc) if arr_time else departure

        deep_links = generate_deep_links(
            request.origin, request.destination, request.mode, departure=departure,
        )

        return RouteResult(
            origin=leg.get("start_address", request.origin),
            destination=leg.get("end_address", request.destination),
            mode=request.mode,
            duration_seconds=leg["duration"]["value"],
            departure=departure,
            arrival=arrival_dt,
            steps=steps,
            deep_links=deep_links,
        )


def _parse_step(step: dict) -> RouteStep:
    transit = step.get("transit_details", {})
    return RouteStep(
        instruction=step.get("html_instructions", ""),
        mode=step.get("travel_mode", "").lower(),
        distance_meters=step.get("distance", {}).get("value", 0),
        duration_seconds=step.get("duration", {}).get("value", 0),
        transit_line=transit.get("line", {}).get("short_name"),
        transit_stops=transit.get("num_stops"),
    )
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_google_maps.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/kit/errors.py src/kit/route/google_maps.py tests/test_google_maps.py
git commit -m "feat: Google Maps Directions client with error handling"
```

---

## Task 7: Public Route API (plan_route)

**Files:**
- Modify: `src/kit/route/__init__.py`
- Create: `src/kit/route/planner.py`
- Create: `tests/test_planner.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_planner.py
import pytest
from unittest.mock import patch, MagicMock
from kit.route.planner import plan_route, plan_multi_route
from kit.route.core import RouteRequest, RouteResult, TransportMode
from kit.config import KitConfig


@pytest.fixture
def mock_router():
    with patch("kit.route.planner._get_router") as mock:
        router = MagicMock()
        mock.return_value = router
        yield router


@pytest.fixture
def sample_result():
    from datetime import datetime, timezone, timedelta
    from kit.route.core import DeepLinks
    return RouteResult(
        origin="A", destination="B",
        mode=TransportMode.TRANSIT,
        duration_seconds=600,
        departure=datetime(2026, 3, 25, 18, 0, tzinfo=timezone(timedelta(hours=1))),
        arrival=datetime(2026, 3, 25, 18, 10, tzinfo=timezone(timedelta(hours=1))),
        steps=[], deep_links=DeepLinks(google_maps="https://maps.google.com"),
    )


def test_plan_route_string_args(mock_router, sample_result):
    mock_router.plan.return_value = sample_result
    result = plan_route("A", "B")
    assert result.duration_seconds == 600
    mock_router.plan.assert_called_once()


def test_plan_route_request_object(mock_router, sample_result):
    mock_router.plan.return_value = sample_result
    req = RouteRequest(origin="A", destination="B", mode=TransportMode.WALKING)
    result = plan_route(req)
    assert result.duration_seconds == 600


def test_plan_multi_route(mock_router, sample_result):
    mock_router.plan.return_value = sample_result
    results = plan_multi_route(["A", "B", "C"])
    assert len(results) == 2  # A->B, B->C
    assert mock_router.plan.call_count == 2
```

- [ ] **Step 2: Run tests — expect fail**

- [ ] **Step 3: Implement planner.py**

```python
# src/kit/route/planner.py
"""High-level route planning API."""

from __future__ import annotations

from typing import overload

from kit.config import KitConfig, load_config
from kit.errors import ConfigError
from kit.route.core import RouteRequest, RouteResult, TransportMode
from kit.route.google_maps import GoogleMapsRouter
from kit.utils.geo import parse_location


def _get_router(config: KitConfig | None = None) -> GoogleMapsRouter:
    config = config or load_config()
    if not config.google_maps_api_key:
        raise ConfigError("Google Maps API key not configured. Run: kit setup")
    return GoogleMapsRouter(api_key=config.google_maps_api_key)


@overload
def plan_route(origin: str, destination: str, /, **kwargs) -> RouteResult: ...

@overload
def plan_route(request: RouteRequest, /) -> RouteResult: ...

def plan_route(origin_or_request, destination=None, /, **kwargs) -> RouteResult:
    config = load_config()
    router = _get_router(config)

    if isinstance(origin_or_request, RouteRequest):
        request = origin_or_request
    else:
        origin_loc = parse_location(origin_or_request).resolve(config)
        dest_loc = parse_location(destination).resolve(config)
        request = RouteRequest(origin=origin_loc, destination=dest_loc, **kwargs)

    return router.plan(request)


def plan_multi_route(
    stops: list[str],
    mode: TransportMode = TransportMode.TRANSIT,
    departure: str | None = None,
    config: KitConfig | None = None,
) -> list[RouteResult]:
    config = config or load_config()
    router = _get_router(config)
    results = []
    for i in range(len(stops) - 1):
        origin = parse_location(stops[i]).resolve(config)
        dest = parse_location(stops[i + 1]).resolve(config)
        req = RouteRequest(origin=origin, destination=dest, mode=mode)
        results.append(router.plan(req))
    return results
```

- [ ] **Step 4: Update route/__init__.py**

```python
# src/kit/route/__init__.py
from kit.route.core import RouteRequest, RouteResult, RouteStep, TransportMode, DeepLinks
from kit.route.planner import plan_route, plan_multi_route

__all__ = [
    "RouteRequest", "RouteResult", "RouteStep", "TransportMode", "DeepLinks",
    "plan_route", "plan_multi_route",
]
```

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/test_planner.py -v`

- [ ] **Step 6: Commit**

```bash
git add src/kit/route/ tests/test_planner.py
git commit -m "feat: public plan_route/plan_multi_route API with overloaded signatures"
```

---

## Task 8: Formatting Utilities

**Files:**
- Create: `src/kit/utils/formatting.py`

- [ ] **Step 1: Implement formatting.py** (utility, tested via CLI/integration tests)

```python
# src/kit/utils/formatting.py
"""Human-readable formatting for CLI output."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from kit.route.core import RouteResult, TransportMode

_MODE_EMOJI = {
    TransportMode.TRANSIT: "\U0001f687",   # 🚇
    TransportMode.WALKING: "\U0001f6b6",   # 🚶
    TransportMode.BICYCLING: "\U0001f6b2", # 🚲
    TransportMode.DRIVING: "\U0001f697",   # 🚗
}

console = Console()


def print_route(result: RouteResult) -> None:
    emoji = _MODE_EMOJI.get(result.mode, "")
    console.print(
        f"\n{emoji} [bold]{result.origin}[/bold] → [bold]{result.destination}[/bold]"
    )
    console.print(
        f"   {result.mode.value.title()} · {result.duration_human} · "
        f"Abfahrt {result.departure.strftime('%H:%M')} → "
        f"Ankunft {result.arrival.strftime('%H:%M')}\n"
    )
    for i, step in enumerate(result.steps, 1):
        parts = [f"   {i}. {step.instruction}"]
        if step.transit_line:
            parts.append(f" · {step.transit_stops} Stationen")
        parts.append(f" · {step.duration_human}")
        console.print("".join(parts))

    console.print()
    if result.deep_links.google_maps:
        console.print(f"   \U0001f4ce Google Maps: {result.deep_links.google_maps}")
    if result.deep_links.db_navigator:
        console.print(f"   \U0001f4ce DB Navigator: {result.deep_links.db_navigator}")
    if result.deep_links.apple_maps:
        console.print(f"   \U0001f4ce Apple Maps: {result.deep_links.apple_maps}")
    console.print()
```

- [ ] **Step 2: Commit**

```bash
git add src/kit/utils/formatting.py
git commit -m "feat: Rich formatting for route output"
```

---

## Task 9: Route CLI Commands

**Files:**
- Create: `src/kit/route/commands.py`
- Create: `src/kit/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI integration tests**

```python
# tests/test_cli.py
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from kit.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_route_help():
    result = runner.invoke(app, ["route", "--help"])
    assert result.exit_code == 0
    assert "origin" in result.output.lower() or "ORIGIN" in result.output


@patch("kit.route.commands.plan_route")
def test_route_json_output(mock_plan):
    from datetime import datetime, timezone, timedelta
    from kit.route.core import RouteResult, TransportMode, DeepLinks
    mock_plan.return_value = RouteResult(
        origin="A", destination="B", mode=TransportMode.TRANSIT,
        duration_seconds=600,
        departure=datetime(2026, 3, 25, 18, 0, tzinfo=timezone(timedelta(hours=1))),
        arrival=datetime(2026, 3, 25, 18, 10, tzinfo=timezone(timedelta(hours=1))),
        steps=[], deep_links=DeepLinks(google_maps="https://maps.google.com"),
    )
    result = runner.invoke(app, ["route", "A", "B", "--json"])
    assert result.exit_code == 0
    assert '"duration_seconds": 600' in result.output
```

- [ ] **Step 2: Implement route/commands.py and cli.py**

```python
# src/kit/route/commands.py
"""CLI commands for kit route."""

from __future__ import annotations

import json
import sys
from datetime import datetime

import typer
from rich.console import Console

from kit.errors import KitError
from kit.route.core import TransportMode
from kit.route.planner import plan_route
from kit.utils.formatting import print_route

route_app = typer.Typer(help="Route planning between locations.")
console = Console(stderr=True)


@route_app.command("plan")
@route_app.command("", hidden=True)  # default subcommand
def route_plan(
    origin: str = typer.Argument(..., help="Start: address, lat,lng, or 'home'"),
    destination: str = typer.Argument(..., help="End: address, lat,lng, or 'home'"),
    mode: TransportMode = typer.Option(TransportMode.TRANSIT, "--mode", "-m"),
    depart: str | None = typer.Option(None, "--depart", "-d", help="Departure HH:MM or ISO-8601"),
    arrive: str | None = typer.Option(None, "--arrive", "-a", help="Arrival HH:MM or ISO-8601"),
    output_json: bool = typer.Option(False, "--json", help="JSON output"),
    link: bool = typer.Option(False, "--link", help="Show deep links"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Calculate a route between two locations."""
    if depart and arrive:
        console.print("[red]Error: --depart and --arrive are mutually exclusive[/red]")
        raise typer.Exit(1)

    try:
        result = plan_route(origin, destination, mode=mode)
    except KitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)

    if output_json:
        print(result.model_dump_json(indent=2))
    else:
        print_route(result)
```

```python
# src/kit/cli.py
"""Kit CLI — Agentic-ready personal toolbox."""

from __future__ import annotations

import typer

from kit import __version__
from kit.route.commands import route_app

app = typer.Typer(
    name="kit",
    help="Agentic-ready personal CLI toolbox.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        print(f"kit {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True),
) -> None:
    pass


app.add_typer(route_app, name="route")
```

- [ ] **Step 3: Run tests — expect pass**

Run: `pytest tests/test_cli.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/kit/cli.py src/kit/route/commands.py tests/test_cli.py
git commit -m "feat: kit route CLI with JSON output, deep links, Rich formatting"
```

---

## Task 10: Calendar Core + Google Calendar Client

**Files:**
- Create: `src/kit/cal/__init__.py`
- Create: `src/kit/cal/core.py`
- Create: `src/kit/cal/google_cal.py`
- Create: `tests/test_cal_core.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cal_core.py
import pytest
from datetime import datetime, timezone, timedelta
from kit.cal.core import CalendarEvent, TravelBuffer


def test_calendar_event_basic():
    ev = CalendarEvent(
        title="Dinner", start=datetime(2026, 3, 25, 19, 0, tzinfo=timezone(timedelta(hours=1))),
        duration_minutes=60, location="Oranienstr 42",
    )
    assert ev.end.hour == 20


def test_calendar_event_all_day():
    ev = CalendarEvent(title="Urlaub", all_day=True, date="2026-03-25")
    assert ev.all_day is True


def test_travel_buffer():
    buf = TravelBuffer(
        title="Anreise: Dinner",
        start=datetime(2026, 3, 25, 18, 33, tzinfo=timezone(timedelta(hours=1))),
        end=datetime(2026, 3, 25, 18, 55, tzinfo=timezone(timedelta(hours=1))),
        description="U8 · 22 min\nhttps://maps.google.com/...",
    )
    assert "Anreise" in buf.title
```

- [ ] **Step 2: Implement cal/core.py**

```python
# src/kit/cal/__init__.py
from kit.cal.core import CalendarEvent, TravelBuffer

__all__ = ["CalendarEvent", "TravelBuffer"]

# src/kit/cal/core.py
"""Calendar event data models."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, computed_field


class CalendarEvent(BaseModel):
    title: str
    start: datetime | None = None
    duration_minutes: int = 60
    location: str | None = None
    description: str | None = None
    calendar_id: str = "primary"
    all_day: bool = False
    date: str | None = None  # YYYY-MM-DD for all-day events

    @computed_field
    @property
    def end(self) -> datetime | None:
        if self.start:
            return self.start + timedelta(minutes=self.duration_minutes)
        return None


class TravelBuffer(BaseModel):
    title: str
    start: datetime
    end: datetime
    description: str = ""
    calendar_id: str = "primary"
```

- [ ] **Step 3: Implement cal/google_cal.py** (mock-based, real OAuth tested via smoke tests)

```python
# src/kit/cal/google_cal.py
"""Google Calendar API client."""

from __future__ import annotations

from pathlib import Path

from kit.cal.core import CalendarEvent, TravelBuffer
from kit.errors import CalendarError


class GoogleCalendarClient:
    def __init__(self, credentials_dir: Path | None = None) -> None:
        self._credentials_dir = credentials_dir
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_path = (self._credentials_dir or Path.home() / ".config" / "kit") / "token.json"
            if not token_path.exists():
                raise CalendarError("Not authenticated. Run: kit setup")
            creds = Credentials.from_authorized_user_file(str(token_path))
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                token_path.write_text(creds.to_json())
            self._service = build("calendar", "v3", credentials=creds)
            return self._service
        except CalendarError:
            raise
        except Exception as e:
            raise CalendarError(f"Calendar auth error: {e}") from e

    def add_event(self, event: CalendarEvent) -> dict:
        service = self._get_service()
        body: dict = {
            "summary": event.title,
            "location": event.location or "",
            "description": event.description or "",
        }
        if event.all_day and event.date:
            body["start"] = {"date": event.date}
            body["end"] = {"date": event.date}
        elif event.start and event.end:
            body["start"] = {"dateTime": event.start.isoformat(), "timeZone": "Europe/Berlin"}
            body["end"] = {"dateTime": event.end.isoformat(), "timeZone": "Europe/Berlin"}
        else:
            raise CalendarError("Event must have start time or be all-day")

        try:
            return service.events().insert(calendarId=event.calendar_id, body=body).execute()
        except Exception as e:
            raise CalendarError(f"Failed to create event: {e}") from e

    def add_travel_buffer(self, buffer: TravelBuffer) -> dict:
        service = self._get_service()
        body = {
            "summary": f"\U0001f687 {buffer.title}",
            "description": buffer.description,
            "start": {"dateTime": buffer.start.isoformat(), "timeZone": "Europe/Berlin"},
            "end": {"dateTime": buffer.end.isoformat(), "timeZone": "Europe/Berlin"},
            "colorId": "8",  # Graphite/grey
        }
        try:
            return service.events().insert(calendarId=buffer.calendar_id, body=body).execute()
        except Exception as e:
            raise CalendarError(f"Failed to create travel buffer: {e}") from e

    def list_events(self, calendar_id: str = "primary", time_min: str | None = None, time_max: str | None = None, max_results: int = 20) -> list[dict]:
        service = self._get_service()
        kwargs: dict = {"calendarId": calendar_id, "maxResults": max_results, "singleEvents": True, "orderBy": "startTime"}
        if time_min:
            kwargs["timeMin"] = time_min
        if time_max:
            kwargs["timeMax"] = time_max
        try:
            result = service.events().list(**kwargs).execute()
            return result.get("items", [])
        except Exception as e:
            raise CalendarError(f"Failed to list events: {e}") from e
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_cal_core.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/kit/cal/ tests/test_cal_core.py
git commit -m "feat: calendar core models and Google Calendar client"
```

---

## Task 11: Calendar CLI Commands

**Files:**
- Create: `src/kit/cal/commands.py`
- Modify: `src/kit/cli.py` (add cal subcommand)

- [ ] **Step 1: Implement cal/commands.py**

```python
# src/kit/cal/commands.py
"""CLI commands for kit cal."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import dateparser
import typer
from rich.console import Console
from rich.table import Table

from kit.cal.core import CalendarEvent, TravelBuffer
from kit.cal.google_cal import GoogleCalendarClient
from kit.errors import KitError
from kit.route.planner import plan_route

cal_app = typer.Typer(help="Calendar management.")
console = Console(stderr=True)


@cal_app.command()
def add(
    title: str = typer.Argument(..., help="Event title"),
    start: str | None = typer.Option(None, "--start", "-s", help="Start time HH:MM"),
    date: str | None = typer.Option(None, "--date", help="Date (YYYY-MM-DD, morgen, freitag)"),
    duration: str = typer.Option("1h", "--duration", help="Duration (e.g. 1h, 30m)"),
    location: str | None = typer.Option(None, "--location", "-l"),
    route_from: str | None = typer.Option(None, "--route-from", help="Add travel buffer from location"),
    description: str | None = typer.Option(None, "--description"),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Create a calendar event."""
    try:
        # Parse date
        event_date = _parse_date(date) if date else datetime.now().date()

        if start:
            h, m = int(start.split(":")[0]), int(start.split(":")[1])
            tz = timezone(timedelta(hours=1))  # CET
            start_dt = datetime(event_date.year, event_date.month, event_date.day, h, m, tzinfo=tz)
            event = CalendarEvent(
                title=title, start=start_dt, duration_minutes=_parse_duration(duration),
                location=location, description=description,
            )
        else:
            event = CalendarEvent(
                title=title, all_day=True, date=str(event_date),
                location=location, description=description,
            )

        client = GoogleCalendarClient()

        # Travel buffer
        if route_from and start:
            try:
                route_result = plan_route(route_from, location or title, mode="transit")
                buffer_minutes = 5
                travel_end = start_dt - timedelta(minutes=buffer_minutes)
                travel_start = travel_end - timedelta(seconds=route_result.duration_seconds)
                links = f"Google Maps: {route_result.deep_links.google_maps}"
                if route_result.deep_links.db_navigator:
                    links += f"\nDB Navigator: {route_result.deep_links.db_navigator}"
                buffer = TravelBuffer(
                    title=f"Anreise: {title}",
                    start=travel_start, end=travel_end,
                    description=f"{route_result.duration_human} · {route_result.mode.value}\n{links}",
                )
                client.add_travel_buffer(buffer)
                console.print(f"[green]✓ Travel buffer: {travel_start.strftime('%H:%M')}-{travel_end.strftime('%H:%M')}[/green]")
            except KitError as e:
                console.print(f"[yellow]⚠ Route failed: {e}. Event created without buffer.[/yellow]")

        result = client.add_event(event)
        if output_json:
            print(json.dumps(result, indent=2, default=str))
        else:
            console.print(f"[green]✓ Event created: {title}[/green]")
    except KitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)


@cal_app.command()
def today(output_json: bool = typer.Option(False, "--json")) -> None:
    """Show today's events."""
    _list_events("today", output_json)


@cal_app.command()
def tomorrow(output_json: bool = typer.Option(False, "--json")) -> None:
    """Show tomorrow's events."""
    _list_events("tomorrow", output_json)


@cal_app.command()
def week(output_json: bool = typer.Option(False, "--json")) -> None:
    """Show this week's events."""
    _list_events("week", output_json)


def _list_events(range_name: str, output_json: bool) -> None:
    now = datetime.now(tz=timezone(timedelta(hours=1)))
    if range_name == "today":
        time_min = now.replace(hour=0, minute=0, second=0).isoformat()
        time_max = now.replace(hour=23, minute=59, second=59).isoformat()
    elif range_name == "tomorrow":
        tmrw = now + timedelta(days=1)
        time_min = tmrw.replace(hour=0, minute=0, second=0).isoformat()
        time_max = tmrw.replace(hour=23, minute=59, second=59).isoformat()
    else:
        time_min = now.isoformat()
        time_max = (now + timedelta(days=7)).isoformat()

    try:
        client = GoogleCalendarClient()
        events = client.list_events(time_min=time_min, time_max=time_max)
        if output_json:
            print(json.dumps(events, indent=2, default=str))
        else:
            if not events:
                Console().print("[dim]No events.[/dim]")
                return
            table = Table(title=f"Events ({range_name})")
            table.add_column("Time", style="cyan")
            table.add_column("Title", style="bold")
            table.add_column("Location", style="dim")
            for ev in events:
                start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", ""))
                if "T" in start:
                    start = start[11:16]
                table.add_row(start, ev.get("summary", ""), ev.get("location", ""))
            Console().print(table)
    except KitError as e:
        Console(stderr=True).print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)


def _parse_date(date_str: str):
    parsed = dateparser.parse(date_str, languages=["de", "en"])
    if parsed:
        return parsed.date()
    raise ValueError(f"Could not parse date: {date_str}")


def _parse_duration(duration_str: str) -> int:
    duration_str = duration_str.strip().lower()
    if duration_str.endswith("h"):
        return int(float(duration_str[:-1]) * 60)
    if duration_str.endswith("m"):
        return int(duration_str[:-1])
    return int(duration_str)
```

- [ ] **Step 2: Register cal_app in cli.py**

Add to `src/kit/cli.py`:
```python
from kit.cal.commands import cal_app
app.add_typer(cal_app, name="cal")
```

- [ ] **Step 3: Test CLI help**

Run: `kit cal --help`
Expected: Shows add, today, tomorrow, week subcommands

- [ ] **Step 4: Commit**

```bash
git add src/kit/cal/commands.py src/kit/cli.py
git commit -m "feat: kit cal CLI with add, today, tomorrow, week commands"
```

---

## Task 12: MCP Server

**Files:**
- Create: `src/kit/mcp_server.py`
- Create: `src/kit/route/mcp_tools.py`
- Create: `src/kit/cal/mcp_tools.py`
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Implement route MCP tools**

```python
# src/kit/route/mcp_tools.py
"""MCP tool registrations for route planning."""

from __future__ import annotations

from mcp.server import Server

from kit.config import KitConfig
from kit.route.core import RouteRequest, TransportMode
from kit.route.planner import plan_route, plan_multi_route


def register_route_tools(server: Server, config: KitConfig) -> None:
    @server.tool()
    async def kit_route(
        origin: str,
        destination: str,
        mode: str = "transit",
        departure_time: str | None = None,
        arrival_time: str | None = None,
    ) -> str:
        """Calculate a route between two locations using Google Maps. Returns duration, steps, and deep links to navigation apps. Supports addresses, coordinates (lat,lng), and saved locations like 'home'."""
        result = plan_route(origin, destination, mode=TransportMode(mode))
        return result.model_dump_json(indent=2)

    @server.tool()
    async def kit_route_multi(
        stops: list[str],
        mode: str = "transit",
        departure_time: str | None = None,
    ) -> str:
        """Calculate routes between multiple stops in sequence. Returns total travel time and per-leg details."""
        results = plan_multi_route(stops, mode=TransportMode(mode))
        total = sum(r.duration_seconds for r in results)
        return {
            "total_duration_seconds": total,
            "total_duration_human": f"{total // 3600}h {(total % 3600) // 60}min" if total >= 3600 else f"{total // 60} min",
            "legs": [r.model_dump() for r in results],
        }
```

- [ ] **Step 2: Implement cal MCP tools**

```python
# src/kit/cal/mcp_tools.py
"""MCP tool registrations for calendar."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import dateparser
from mcp.server import Server

from kit.cal.commands import _parse_duration
from kit.cal.core import CalendarEvent, TravelBuffer
from kit.cal.google_cal import GoogleCalendarClient
from kit.config import KitConfig
from kit.errors import KitError
from kit.route.planner import plan_route


def register_cal_tools(server: Server, config: KitConfig) -> None:
    @server.tool()
    async def kit_cal_add(
        title: str,
        start: str,
        date: str | None = None,
        duration_minutes: int = 60,
        location: str | None = None,
        description: str | None = None,
        route_from: str | None = None,
        route_to: str | None = None,
        calendar_id: str = "primary",
    ) -> str:
        """Create a Google Calendar event. Syncs automatically to Notion Calendar and Apple Calendar. Can calculate and add a travel buffer event with navigation deep links."""
        tz = timezone(timedelta(hours=1))
        event_date = dateparser.parse(date, languages=["de", "en"]).date() if date else datetime.now(tz=tz).date()
        h, m = int(start.split(":")[0]), int(start.split(":")[1])
        start_dt = datetime(event_date.year, event_date.month, event_date.day, h, m, tzinfo=tz)

        event = CalendarEvent(
            title=title, start=start_dt, duration_minutes=duration_minutes,
            location=location, description=description, calendar_id=calendar_id,
        )

        client = GoogleCalendarClient()
        results = {"event": None, "travel_buffer": None, "warnings": []}

        if route_from and location:
            try:
                route_result = plan_route(route_from, location)
                travel_end = start_dt - timedelta(minutes=5)
                travel_start = travel_end - timedelta(seconds=route_result.duration_seconds)
                links = f"Google Maps: {route_result.deep_links.google_maps}"
                if route_result.deep_links.db_navigator:
                    links += f"\nDB Navigator: {route_result.deep_links.db_navigator}"
                buffer = TravelBuffer(
                    title=f"Anreise: {title}", start=travel_start, end=travel_end,
                    description=f"{route_result.duration_human} · {route_result.mode.value}\n{links}",
                    calendar_id=calendar_id,
                )
                buf_result = client.add_travel_buffer(buffer)
                results["travel_buffer"] = {
                    "start": travel_start.isoformat(), "end": travel_end.isoformat(),
                    "duration": route_result.duration_human,
                    "deep_links": route_result.deep_links.model_dump(),
                }
            except KitError as e:
                results["warnings"].append(f"Route calculation failed: {e}. Event created without travel buffer.")

        ev_result = client.add_event(event)
        results["event"] = {"id": ev_result.get("id"), "start": start_dt.isoformat(), "title": title}
        return json.dumps(results, indent=2, default=str)

    @server.tool()
    async def kit_cal_list(
        range: str = "today",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> str:
        """List calendar events for a given time range."""
        client = GoogleCalendarClient()
        tz = timezone(timedelta(hours=1))
        now = datetime.now(tz=tz)
        if range == "today":
            t_min = now.replace(hour=0, minute=0).isoformat()
            t_max = now.replace(hour=23, minute=59).isoformat()
        elif range == "tomorrow":
            tmrw = now + timedelta(days=1)
            t_min = tmrw.replace(hour=0, minute=0).isoformat()
            t_max = tmrw.replace(hour=23, minute=59).isoformat()
        elif range == "week":
            t_min = now.isoformat()
            t_max = (now + timedelta(days=7)).isoformat()
        else:
            t_min = start_date or now.isoformat()
            t_max = end_date or (now + timedelta(days=1)).isoformat()
        events = client.list_events(time_min=t_min, time_max=t_max)
        return json.dumps(events, indent=2, default=str)
```

- [ ] **Step 3: Implement mcp_server.py**

```python
# src/kit/mcp_server.py
"""Kit MCP Server — exposes all kit tools for Claude Code."""

from __future__ import annotations

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server

from kit.cal.mcp_tools import register_cal_tools
from kit.config import load_config
from kit.route.mcp_tools import register_route_tools

server = Server("kit")


async def main() -> None:
    config = load_config()
    register_route_tools(server, config)
    register_cal_tools(server, config)

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def run() -> None:
    """Entry-point for pyproject.toml."""
    asyncio.run(main())
```

- [ ] **Step 4: Run all tests**

Run: `pytest -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/kit/mcp_server.py src/kit/route/mcp_tools.py src/kit/cal/mcp_tools.py
git commit -m "feat: MCP Server with kit_route, kit_cal_add, kit_cal_list tools"
```

---

## Task 13: Setup Command

**Files:**
- Modify: `src/kit/cli.py`

- [ ] **Step 1: Add setup command to cli.py**

```python
@app.command()
def setup() -> None:
    """Interactive setup for kit: API keys, OAuth, home address."""
    from rich.console import Console
    from kit.config import KitConfig, save_config, load_config, get_config_dir

    console = Console()
    config = load_config()

    console.print("\n[bold]Welcome to kit![/bold] Let's get you set up.\n")

    # Step 1: Google Maps API Key
    console.print("[bold]1/3 — Google Maps API Key[/bold]")
    console.print("   You need a key with Directions + Geocoding API enabled.")
    console.print("   → Get one at: [link]https://console.cloud.google.com/apis/credentials[/link]")
    api_key = typer.prompt("   Paste your key", default=config.google_maps_api_key or "")
    config.google_maps_api_key = api_key

    # Step 2: Google Calendar OAuth
    console.print("\n[bold]2/3 — Google Calendar[/bold]")
    console.print("   Place your OAuth client credentials file at:")
    console.print(f"   {get_config_dir() / 'credentials.json'}")
    console.print("   → Get it from: [link]https://console.cloud.google.com/apis/credentials[/link]")
    console.print("   (Create an OAuth 2.0 Client ID, download JSON)")
    if typer.confirm("   Ready to authenticate?", default=True):
        _run_oauth_flow(get_config_dir())

    # Step 3: Home address
    console.print("\n[bold]3/3 — Home Address[/bold]")
    home = typer.prompt("   Your default starting point", default=config.home or "")
    config.home = home

    save_config(config)
    console.print("\n[green]✓ Setup complete![/green] Try: kit route home \"Alexanderplatz\"")


def _run_oauth_flow(config_dir):
    from pathlib import Path
    creds_file = config_dir / "credentials.json"
    if not creds_file.exists():
        Console(stderr=True).print(f"[red]credentials.json not found at {creds_file}[/red]")
        return
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(creds_file), scopes=["https://www.googleapis.com/auth/calendar"]
        )
        creds = flow.run_local_server(port=0)
        token_path = config_dir / "token.json"
        token_path.write_text(creds.to_json())
        token_path.chmod(0o600)
        Console().print("   [green]✓ Authenticated![/green]")
    except Exception as e:
        Console(stderr=True).print(f"[red]OAuth failed: {e}[/red]")
```

- [ ] **Step 2: Commit**

```bash
git add src/kit/cli.py
git commit -m "feat: interactive kit setup command for API keys and OAuth"
```

---

## Task 14: README + CI

**Files:**
- Create: `README.md`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write portfolio-ready README**

A professional README with: badges, hero description, installation, quick start, CLI reference, Python API examples, MCP Server setup, architecture diagram, contributing guide.

- [ ] **Step 2: Write CI workflow**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: pytest -v -m "not smoke"
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md .github/
git commit -m "docs: portfolio-ready README and CI workflow"
git push
```

---

## Task 15: Register MCP Server in Claude Code

**Files:**
- Modify: `~/.claude/settings.json`

- [ ] **Step 1: Add kit MCP server to settings**

Add to `mcpServers` in settings.json:
```json
"kit": {
  "command": "/Users/p.fiedler/Desktop/Code_Projects/kit/.venv/bin/kit-mcp",
  "args": []
}
```

- [ ] **Step 2: Verify MCP server starts**

Run: `kit-mcp` (should start and wait for stdio input, Ctrl+C to stop)

- [ ] **Step 3: Commit settings change note in spec**

---

## Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | Project scaffolding | - |
| 2 | Config system | 5 tests |
| 3 | Geo utilities | 8 tests |
| 4 | Route core models | 5 tests |
| 5 | Deep link generation | 6 tests |
| 6 | Google Maps client | 3 tests |
| 7 | Route planner API | 3 tests |
| 8 | Formatting utilities | - |
| 9 | Route CLI | 3 tests |
| 10 | Calendar core + client | 3 tests |
| 11 | Calendar CLI | - |
| 12 | MCP Server | - |
| 13 | Setup command | - |
| 14 | README + CI | - |
| 15 | Register MCP Server | - |

**Total: 15 tasks, ~36 tests, ~15 commits**
