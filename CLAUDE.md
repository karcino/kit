# Kit — Agentic-Ready Personal CLI Toolbox

## Overview

Kit is a modular personal toolbox with three interfaces sharing one core:
- **CLI** (Typer) — human-facing terminal commands
- **Python API** — `from kit.route import plan_route`
- **MCP Server** (stdio) — Claude Code calls `kit_route`, `kit_cal_add`, `kit_plan_day` as native tools

First tools: multimodal route planning (Google Maps) + calendar management (Google Calendar API).

## Architecture

```
src/kit/
├── cli.py              # Typer app, subcommand routing
├── config.py           # TOML config (~/.config/kit/)
├── errors.py           # Exception hierarchy: KitError → ConfigError, APIError, etc.
├── mcp_server.py       # MCP Server entry point (kit-mcp)
├── setup_cmd.py        # Interactive setup wizard
├── route/
│   ├── core.py         # RouteRequest, RouteResult (Pydantic models)
│   ├── google_maps.py  # Google Maps Directions + Geocoding client
│   ├── deep_links.py   # URL generator: Google Maps, DB Navigator, Apple Maps, BVG
│   ├── planner.py      # plan_day() — multi-stop day planning
│   └── commands.py     # CLI subcommands for "kit route"
├── cal/
│   ├── core.py         # CalendarEvent model
│   └── google_cal.py   # Google Calendar API client
└── utils/
    ├── geo.py          # Coordinate parsing, geocoding helpers
    └── formatting.py   # Rich tables, human-readable output
```

All three interfaces call the same core functions. No logic duplication.

## Key Conventions

- **TDD** — write tests first, implementation second
- **Pydantic models** — all data structures use Pydantic v2 for validation and JSON serialization
- **Rich output** — CLI uses Rich for tables, colors, progress bars
- **Typed** — full type hints, checked with mypy
- **VCR cassettes** — API tests use pytest-vcr to record and replay responses
- **Error hierarchy** — all exceptions inherit from `KitError`; CLI maps to exit codes, MCP maps to `isError: true`
- **Config** — TOML at `~/.config/kit/config.toml`, env vars override (`KIT_GOOGLE_MAPS_API_KEY`)

## Common Commands

```bash
# Run tests (skip smoke tests that need real API keys)
pytest -v -m "not smoke"

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/kit/

# Install in dev mode
pip install -e ".[dev]"
```

## MCP Server

Entry point: `kit-mcp` (defined in pyproject.toml `[project.scripts]`).

Registered tools:
- `kit_route` — route between two locations
- `kit_route_multi` — multi-stop route
- `kit_cal_add` — create calendar event with optional travel buffer
- `kit_cal_list` — list events (today/tomorrow/week)
- `kit_plan_day` — full day planning with feasibility check

The MCP server communicates via stdio and is registered in `~/.claude/settings.json`.

## Testing

- Unit tests: coordinate parsing, deep links, formatting (no API calls)
- Integration tests: Google Maps + Calendar clients (VCR cassettes)
- CLI tests: end-to-end via `typer.testing.CliRunner`
- Smoke tests: real API calls, marked with `@pytest.mark.smoke`, excluded from CI
