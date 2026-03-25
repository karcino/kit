# Kit — Agentic-Ready Personal CLI Toolbox

**Three interfaces. One core.** A modular personal toolbox that works equally well from the terminal, as a Python library, and as an MCP Server for AI agents like Claude Code.

[![CI](https://github.com/karcino/kit/actions/workflows/ci.yml/badge.svg)](https://github.com/karcino/kit/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │            kit — Toolbox                    │
                    ├─────────────────────────────────────────────┤
                    │                                             │
  ┌──────────┐      │   ┌──────────┐      ┌───────────────────┐  │
  │ Terminal │─────▶│   │  Route   │─────▶│ Google Maps API   │  │
  │ (Human)  │◀─────│   │  Tool    │      │ (Directions +     │  │
  └──────────┘      │   │          │      │  Geocoding)       │  │
                    │   └──────────┘      └───────────────────┘  │
  ┌──────────┐      │                                             │
  │ Claude   │─────▶│   ┌──────────┐      ┌───────────────────┐  │
  │ Code     │◀─────│   │ Calendar │─────▶│ Google Calendar   │  │
  │ (Agent)  │      │   │  Tool    │      │ → Notion Calendar │  │
  └──────────┘      │   │          │      │ → Apple Calendar  │  │
                    │   └──────────┘      └───────────────────┘  │
  ┌──────────┐      │                                             │
  │ Python   │─────▶│   ┌──────────┐      ┌───────────────────┐  │
  │ Script   │◀─────│   │  Utils   │      │ Deep Links:       │  │
  └──────────┘      │   │ geo, fmt │      │  Google Maps App  │  │
                    │   └──────────┘      │  DB Navigator     │  │
                    │                      │  Apple Maps       │  │
                    │   ┌──────────┐      │  BVG Fahrinfo     │  │
                    │   │ Config   │      └───────────────────┘  │
                    │   │~/.config/│                              │
                    │   │  kit/    │                              │
                    │   └──────────┘                              │
                    └─────────────────────────────────────────────┘
```

CLI, Python API, and MCP Server share the same core logic — no code duplication.

---

## Features

- **Multimodal routing** — transit, walking, bicycling, driving via Google Maps
- **Calendar integration** — create events with automatic travel buffers via Google Calendar API (syncs to Notion Calendar + Apple Calendar)
- **Deep links** — open routes directly in Google Maps, DB Navigator, Apple Maps, BVG Fahrinfo
- **Multi-stop day planning** — plan a full day with feasibility checks and warnings for tight connections
- **MCP Server** — Claude Code calls `kit_route`, `kit_cal_add`, `kit_plan_day` as native tools
- **Smart input** — accepts addresses, coordinates (`52.52,13.40`), or saved locations like `home`
- **Dual output** — human-readable Rich tables or `--json` for machines
- **Response caching** — same route cached for 15 min to save API calls
- **Interactive setup** — `kit setup` walks through API keys, OAuth, and home address

---

## Quick Start

### Install

```bash
# Clone and install in editable mode
git clone https://github.com/karcino/kit.git
cd kit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Setup

```bash
kit setup
# 1/3 — Paste your Google Maps API key (Directions + Geocoding APIs enabled)
# 2/3 — OAuth flow for Google Calendar
# 3/3 — Set your home address
```

### First Route

```bash
kit route home "Alexanderplatz, Berlin" --mode transit
```

```
🚇 Home → Alexanderplatz, Berlin
   Transit · 22 min · Abfahrt 18:30 → Ankunft 18:52

   1. U8 Richtung Hermannstr · 3 Stationen · 7 min
   2. Fuss · 350m · 4 min

   📎 Google Maps: https://maps.google.com/...
   📎 DB Navigator: https://reiseauskunft.bahn.de/...
```

---

## CLI Usage

### Route Planning

```bash
# Basic route (default: transit)
kit route "Kreuzberg" "Friedrichshain"

# With travel mode and departure time
kit route home "Hauptbahnhof" --mode bicycling --depart 18:30

# Arrive by a specific time
kit route home "Kino International" --arrive 20:00

# JSON output for scripting
kit route 52.52,13.40 "Goerlitzer Park" --json

# Open route in Google Maps
kit route home "Alexanderplatz" --open

# Multi-stop route
kit route multi home "Metro Friedrichshain" "Alexanderplatz" home
```

### Calendar

```bash
# Add an event
kit cal add "Team Meeting" --start 14:00 --duration 1h

# Add with travel buffer (auto-calculates route from home)
kit cal add "Dinner bei Luigi" --start 19:00 \
  --location "Oranienstr 42, Berlin" --route-from home

# View today's schedule
kit cal today

# View this week
kit cal week
```

### Configuration

```bash
# Interactive setup wizard
kit setup

# Show current config
kit config show

# Update a setting
kit config set general.default_mode bicycling
```

### Options available on all commands

```
--json          Machine-readable JSON output
--verbose, -v   Show detailed step-by-step directions
--no-color      Disable Rich formatting (for piping)
--help          Show help for any command
--version       Show kit version
```

---

## Python API

```python
from kit.route import plan_route, plan_multi_route, RouteRequest

# Simple: two strings
result = plan_route("Alexanderplatz", "Goerlitzer Park")
print(result.duration_human)        # "18 min"
print(result.deep_links.google_maps)  # URL

# Explicit: RouteRequest with all options
result = plan_route(RouteRequest(
    origin="home",
    destination="52.4891,13.3614",
    mode="transit",
    departure="18:30",
))

# Multi-stop
legs = plan_multi_route(
    ["home", "Metro Friedrichshain", "Restaurant Luigi", "home"],
    mode="transit",
    departure="17:00",
)
for leg in legs:
    print(f"{leg.origin_name} → {leg.destination_name}: {leg.duration_human}")
```

### Calendar API

```python
from kit.cal import add_event, CalendarEvent
from kit.route import plan_route

event = CalendarEvent(
    title="Dinner bei Luigi",
    start="2026-03-25T19:00:00",
    duration_minutes=60,
    location="Luigi, Oranienstr 42, Berlin",
)
route = plan_route("home", event.location, mode="transit", arrive_by="19:00")

# Creates event + travel buffer with deep links
add_event(event, travel_buffer=route)
```

### Day Planning

```python
from kit.route import plan_day

plan = plan_day(
    start_location="home",
    stops=[
        {"name": "Metro einkaufen", "location": "Metro Friedrichshain", "duration": "30m"},
        {"name": "Dinner", "location": "Luigi, Oranienstr 42", "duration": "2h", "fixed_time": "19:30"},
    ],
    end_location="home",
    mode="transit",
)

print(plan.is_feasible)        # True / False
print(plan.total_travel_time)  # "1h 12min"
print(plan.warnings)           # ["Tight: only 8 min between Metro and Dinner"]
```

---

## MCP Server (Claude Code Integration)

Kit runs as an [MCP](https://modelcontextprotocol.io/) server so Claude Code can call its tools natively.

### Setup

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "kit": {
      "command": "/path/to/kit/.venv/bin/kit-mcp",
      "args": []
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `kit_route` | Calculate route between two locations |
| `kit_route_multi` | Multi-stop route calculation |
| `kit_cal_add` | Create calendar event with optional travel buffer |
| `kit_cal_list` | List events for today / tomorrow / week |
| `kit_plan_day` | Plan a full day with feasibility checks |

### Example Agent Workflow

```
You:    "I have dinner at Luigi's at 19:30. How do I get there?"

Claude: → calls kit_route(origin="home", destination="Luigi, Oranienstr 42",
                           mode="transit", arrival_time="19:30")
        "Transit, 22 min. You need to leave at 19:08.
         Shall I add a travel buffer to your calendar?"

You:    "Yes, do it."

Claude: → calls kit_cal_add(title="Dinner bei Luigi", start="19:30",
                            location="Luigi, Oranienstr 42", route_from="home")
        "Done — two events created: travel buffer 19:08-19:30 and dinner 19:30-21:30."
```

---

## Configuration

Config lives at `~/.config/kit/config.toml`:

```toml
[general]
default_mode = "transit"         # transit | walking | bicycling | driving
home = "Beispielstr 42, 10999 Berlin"

[google_maps]
api_key = "AIza..."              # or set KIT_GOOGLE_MAPS_API_KEY env var

[google_calendar]
calendar_id = "primary"
# OAuth credentials: ~/.config/kit/credentials.json
# Access token:      ~/.config/kit/token.json (auto-generated)
```

---

## Development

### Prerequisites

- Python 3.11+
- Google Maps API key (Directions + Geocoding APIs)
- Google Calendar OAuth credentials

### Setup

```bash
git clone https://github.com/karcino/kit.git
cd kit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests (offline — uses VCR cassettes)
pytest -v

# Skip smoke tests that hit real APIs
pytest -v -m "not smoke"

# Run with coverage
pytest --cov=kit --cov-report=term-missing
```

### Linting and Type Checking

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/kit/
```

### Project Structure

```
kit/
├── src/kit/
│   ├── cli.py              # Typer CLI with subcommand routing
│   ├── config.py           # TOML config management
│   ├── mcp_server.py       # MCP Server (stdio)
│   ├── route/
│   │   ├── core.py         # RouteRequest, RouteResult models
│   │   ├── google_maps.py  # Google Maps Directions client
│   │   ├── deep_links.py   # URL generator for nav apps
│   │   ├── planner.py      # Multi-stop day planning
│   │   └── commands.py     # CLI subcommands
│   ├── cal/
│   │   ├── core.py         # CalendarEvent model
│   │   └── google_cal.py   # Google Calendar API client
│   └── utils/
│       ├── geo.py          # Coordinate parsing, geocoding
│       └── formatting.py   # Rich output formatting
├── tests/                  # pytest + VCR cassettes
├── docs/specs/             # Design documents
└── pyproject.toml          # Build config, dependencies, entry points
```

---

## Roadmap

- [ ] **BVG API integration** — real-time Berlin public transit data
- [ ] **Alternative routing backends** — HERE Maps, MOTIS (open source)
- [ ] **Multi-modal optimization** — combine transit + bicycling legs
- [ ] **Weather-aware routing** — warn when rain is expected for walking/cycling
- [ ] **Cost tracking** — monitor Google Maps API usage
- [ ] **Additional tools** — `kit finance`, `kit notify`, `kit scrape`

---

## License

[MIT](LICENSE) — Paul Fiedler
