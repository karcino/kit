# Kit — Agentic-Ready Personal Toolbox

**Date:** 2026-03-25
**Status:** Draft
**Author:** Paul Fiedler + Claude

---

## System Overview

```
╔══════════════════════════════════════════════════════════════════════╗
║                        kit — Toolbox                                ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐   ║
║   │  INTERFACES │   │    TOOLS    │   │      EXTERNAL APIs      │   ║
║   ├─────────────┤   ├─────────────┤   ├─────────────────────────┤   ║
║   │             │   │             │   │                         │   ║
║   │  CLI        │──▶│  Route      │──▶│  Google Maps Directions │   ║
║   │  (Typer)    │   │  ┌────────┐ │   │  Google Maps Geocoding  │   ║
║   │             │   │  │ core   │ │   │                         │   ║
║   ├─────────────┤   │  │ gmaps  │ │   ├─────────────────────────┤   ║
║   │             │   │  │ links  │ │   │                         │   ║
║   │  MCP Server │──▶│  │planner │ │   │  Google Calendar API    │   ║
║   │  (stdio)    │   │  └────────┘ │   │    ↓                    │   ║
║   │             │   │             │   │  Notion Calendar (sync) │   ║
║   ├─────────────┤   │  Calendar   │──▶│  Apple Calendar (sync)  │   ║
║   │             │   │  ┌────────┐ │   │                         │   ║
║   │  Python API │──▶│  │ core   │ │   ├─────────────────────────┤   ║
║   │  (import)   │   │  │ gcal   │ │   │                         │   ║
║   │             │   │  └────────┘ │   │  Deep Links:            │   ║
║   └─────────────┘   │             │   │  · Google Maps App/Web  │   ║
║                     │  ┌────────┐ │   │  · DB Navigator         │   ║
║   ┌─────────────┐   │  │ utils  │ │   │  · Apple Maps           │   ║
║   │   CONFIG    │   │  │ geo    │ │   │  · BVG Fahrinfo         │   ║
║   │ ~/.config/  │──▶│  │ format │ │   │                         │   ║
║   │   kit/      │   │  └────────┘ │   └─────────────────────────┘   ║
║   └─────────────┘   └─────────────┘                                  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  Cache: ~/.cache/kit/   │   Tests: pytest + VCR   │   CI: GitHub    ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Data Flow — Termin mit Reise-Puffer:**
```
User/Agent                    kit                         External
    │                          │                              │
    │  "Dinner 19:00           │                              │
    │   Luigi, Oranienstr"     │                              │
    │─────────────────────────▶│                              │
    │                          │  Geocode "Oranienstr 42"     │
    │                          │─────────────────────────────▶│ Google Maps
    │                          │◀─────────────────────────────│ → 52.50,13.42
    │                          │                              │
    │                          │  Directions home → 52.50,13  │
    │                          │─────────────────────────────▶│ Google Maps
    │                          │◀─────────────────────────────│ → 22 min transit
    │                          │                              │
    │                          │  Create Event 1: Travel      │
    │                          │  18:33–18:55 + Deep Links    │
    │                          │─────────────────────────────▶│ Google Calendar
    │                          │                              │  ↓ auto-sync
    │                          │  Create Event 2: Dinner      │  Notion Calendar
    │                          │  19:00–20:00                 │  Apple Calendar
    │                          │─────────────────────────────▶│ Google Calendar
    │                          │                              │
    │  ✓ 2 Events erstellt     │                              │
    │  Travel: 22 min, U8      │                              │
    │◀─────────────────────────│                              │
```

---

## Table of Contents

1. [Vision](#1-vision)
2. [Architektur](#2-architektur)
   - 2.1 [Repo-Struktur](#21-repo-struktur)
   - 2.2 [Tech Stack](#22-tech-stack)
   - 2.3 [Config-System](#23-config-system)
3. [Route-Tool — Detaildesign](#3-route-tool--detaildesign)
   - 3.1 [Input-Formate](#31-input-formate)
   - 3.2 [CLI Interface](#32-cli-interface)
   - 3.3 [Output-Formate](#33-output-formate)
   - 3.4 [Python API](#34-python-api-fuer-agent-nutzung)
   - 3.5 [Deep Links](#35-deep-links)
4. [Calendar-Tool — Detaildesign](#4-calendar-tool--detaildesign)
   - 4.1 [Architektur-Entscheidung](#41-architektur-entscheidung)
   - 4.2 [CLI Interface](#42-cli-interface)
   - 4.3 [Route-Integration](#43-route-integration)
   - 4.4 [Python API](#44-python-api)
5. [Multi-Stop Tagesplanung](#5-multi-stop-tagesplanung-agent-use-case)
6. [Setup-Flow](#6-setup-flow)
7. [Testing-Strategie](#7-testing-strategie)
8. [CLI-Features (Professional Grade)](#8-cli-features-professional-grade)
   - 8.1 [Error Handling](#81-error-handling)
   - 8.2 [Caching und Rate Limiting](#82-caching-und-rate-limiting)
9. [MCP Server — Agent-Native Interface](#9-mcp-server--agent-native-interface)
   - 9.1 [Architektur](#91-architektur)
   - 9.2 [MCP Tool-Definitionen](#92-mcp-tool-definitionen)
   - 9.3 [Claude Code Integration](#93-claude-code-integration)
   - 9.4 [MCP Server Implementierung](#94-mcp-server-implementierung)
10. [Zukunft](#10-zukunft-nicht-im-ersten-build)
11. [Nicht-Ziele](#11-nicht-ziele-explizit-ausgeschlossen)

---

## 1. Vision

`kit` ist eine persoenliche CLI-Toolbox die als Bruecke zwischen Mensch und AI-Agent funktioniert. Jedes Tool hat **drei Interfaces**: ein CLI fuer Paul, eine Python API fuer Scripting, und einen **MCP Server** damit Claude Code die Tools nativ als eigene Werkzeuge aufrufen kann. Das erste Tool ist ein multimodaler Routenplaner.

```bash
kit route "Zuhause" "Alexanderplatz" --mode transit --depart 18:30
kit route 52.52,13.40 "Hauptbahnhof" --mode bicycling --json
```

---

## 2. Architektur

### 2.1 Repo-Struktur

```
kit/
├── README.md                     # Portfolio-ready, professionell
├── LICENSE                       # MIT
├── pyproject.toml                # Single package, entry-points: "kit" CLI + "kit-mcp" Server
├── src/
│   └── kit/
│       ├── __init__.py           # Version, Package-Info
│       ├── cli.py                # Haupt-CLI mit Typer, Subcommand-Routing
│       ├── config.py             # Config-Management (~/.config/kit/)
│       ├── mcp_server.py         # MCP Server — exponiert alle Tools als MCP-Tools
│       ├── route/
│       │   ├── __init__.py
│       │   ├── core.py           # RouteRequest, RouteResult Datenklassen
│       │   ├── google_maps.py    # Google Maps Directions API Client
│       │   ├── deep_links.py     # URL-Generator fuer Apps (GMaps, DB Nav)
│       │   ├── planner.py        # plan_day() — Multi-Stop Tagesplanung (nutzt plan_multi_route)
│       │   ├── commands.py       # CLI Subcommands fuer "kit route"
│       │   └── mcp_tools.py     # MCP Tool-Definitionen fuer Route
│       ├── cal/
│       │   ├── __init__.py
│       │   ├── core.py           # CalendarEvent Datenklasse
│       │   ├── google_cal.py     # Google Calendar API Client
│       │   ├── commands.py       # CLI Subcommands fuer "kit cal"
│       │   └── mcp_tools.py     # MCP Tool-Definitionen fuer Calendar
│       └── utils/
│           ├── __init__.py
│           ├── geo.py            # Koordinaten-Parsing, Geocoding
│           └── formatting.py     # Human-readable Output, Tabellen
├── tests/
│   ├── conftest.py               # Shared Fixtures, Mock-API-Responses
│   ├── test_route_core.py
│   ├── test_route_google_maps.py
│   ├── test_route_deep_links.py
│   ├── test_cal_core.py
│   ├── test_geo.py
│   ├── test_cli.py               # CLI Integration Tests
│   └── test_mcp_server.py        # MCP Server Tests
├── docs/
│   ├── specs/                    # Design Docs (dieses Dokument)
│   └── setup-guide.md            # API Key Setup Anleitung
└── .github/
    └── workflows/
        └── ci.yml                # GitHub Actions: lint + test
```

### 2.2 Tech Stack

| Komponente | Wahl | Grund |
|---|---|---|
| CLI Framework | **Typer** | Moderner Click-Wrapper, Type Hints, Auto-Help |
| Google Maps | **googlemaps** | Offizielle Python-Lib |
| Google Calendar | **google-api-python-client** | Offizielles SDK |
| HTTP | **googlemaps + google-api-python-client** | Offizielle SDKs handhaben HTTP intern. httpx als optionale Dependency fuer zukuenftige Backends |
| Config | **tomllib + tomli-w** | TOML config in ~/.config/kit/ |
| Testing | **pytest + pytest-vcr** | VCR fuer API-Response-Recording |
| Output | **rich** | Schoene Tabellen, Farben, Progress |
| Datenklassen | **pydantic** | Validierung, JSON-Serialisierung |
| MCP Server | **mcp (Python SDK)** | Model Context Protocol Server SDK |

### 2.3 Config-System

```toml
# ~/.config/kit/config.toml

[general]
default_mode = "transit"
home = "Beispielstrasse 42, 10999 Berlin"

[google_maps]
api_key = "AIza..."

[google_calendar]
calendar_id = "primary"
# OAuth credentials in ~/.config/kit/credentials.json
```

API Key kann auch via Environment Variable gesetzt werden: `KIT_GOOGLE_MAPS_API_KEY`.
Config-Datei sollte restriktive Permissions haben (chmod 600).

**OAuth Token Storage:**
- Client Credentials: `~/.config/kit/credentials.json` (aus Google Cloud Console Download)
- Access/Refresh Token: `~/.config/kit/token.json` (automatisch nach OAuth Flow)
- Token Refresh: automatisch via `google-auth` Library
- Bei abgelaufenem Refresh Token: erneuter OAuth Flow via `kit setup --reauth`

**Config Versionierung:**
```toml
[meta]
version = 1  # fuer zukuenftige Migrationen
```

Erster Start: `kit setup` fuehrt interaktiv durch API-Key-Eingabe und Home-Adresse.

---

## 3. Route-Tool — Detaildesign

### 3.1 Input-Formate

```bash
# Adressen (Geocoding via Google Maps)
kit route "Alexanderplatz, Berlin" "Goerlitzer Park"

# Koordinaten (lat,lng)
kit route 52.5200,13.4050 52.4891,13.3614

# Gespeicherte Orte (aus Config)
kit route home "Alexanderplatz"

# Mixed
kit route home 52.5200,13.4050
```

### 3.2 CLI Interface

```bash
kit route <origin> <destination> [OPTIONS]

Optionen:
  --mode, -m      transit | walking | bicycling | driving  [default: transit]
  --depart, -d    Abfahrtszeit (HH:MM oder ISO-8601)       [default: jetzt]
  --arrive, -a    Ankunftszeit (HH:MM oder ISO-8601)
  --alternatives  Anzahl Alternativen                       [default: 1]
  --json          JSON-Output (fuer Agent-Nutzung)
  --link          Deep Link zu Google Maps / DB Navigator ausgeben
  --open          Deep Link direkt im Browser oeffnen
  --verbose, -v   Detaillierte Schrittanweisungen

# Multi-Stop
kit route multi <stop1> <stop2> <stop3> ... [OPTIONS]

# --depart und --arrive sind mutually exclusive (Fehler wenn beide angegeben)
```

**Zeitzonen:** Alle HH:MM-Eingaben werden als lokale Systemzeit interpretiert. ISO-8601 mit explizitem Offset wird respektiert. Alle Rueckgabewerte enthalten Timezone-Information.

### 3.3 Output-Formate

**Human-readable (default):**
```
🚇 Alexanderplatz → Goerlitzer Park
   Transit · 18 min · Abfahrt 18:30 → Ankunft 18:48

   1. U8 Richtung Hermannstr · 3 Stationen · 7 min
   2. Fuss · 350m · 4 min

   📎 Google Maps: https://maps.google.com/...
   📎 DB Navigator: https://reiseauskunft.bahn.de/...
```

**JSON (fuer Agent):**
```json
{
  "origin": "Alexanderplatz, Berlin",
  "destination": "Goerlitzer Park, Berlin",
  "mode": "transit",
  "duration_seconds": 1080,
  "duration_human": "18 min",
  "departure": "2026-03-25T18:30:00+01:00",
  "arrival": "2026-03-25T18:48:00+01:00",
  "steps": [
    {
      "instruction": "U8 Richtung Hermannstr",
      "mode": "transit",
      "distance_meters": 2100,
      "duration_seconds": 420,
      "transit_line": "U8",
      "transit_stops": 3
    },
    {
      "instruction": "Zu Fuss zum Ziel",
      "mode": "walking",
      "distance_meters": 350,
      "duration_seconds": 240,
      "transit_line": null,
      "transit_stops": null
    }
  ],
  "deep_links": {
    "google_maps": "https://www.google.com/maps/dir/?api=1&origin=...",
    "db_navigator": "https://reiseauskunft.bahn.de/bin/query.exe/dn?..."
  }
}
```

### 3.4 Python API (fuer Agent-Nutzung)

```python
from kit.route import plan_route, plan_multi_route, RouteRequest

# Convenience-Form: zwei Strings → intern wird RouteRequest gebaut
result = plan_route("Alexanderplatz", "Goerlitzer Park")
print(result.duration_human)  # "18 min"
print(result.deep_links.google_maps)  # URL

# Explizite Form: RouteRequest-Objekt mit allen Optionen
request = RouteRequest(
    origin="Zuhause",
    destination="52.4891,13.3614",
    mode="transit",
    departure="18:30",
)
result = plan_route(request)

# Signatur: plan_route(origin: str, destination: str, **kwargs) -> RouteResult
#       OR: plan_route(request: RouteRequest) -> RouteResult
# Implementiert via @overload Type Hints.

# Multi-Stop (fuer Tagesplanung)
stops = ["Zuhause", "Metro Friedrichshain", "Restaurant Luigi", "Zuhause"]
results = plan_multi_route(stops, mode="transit", departure="17:00")
for leg in results:
    print(f"{leg.origin_name} → {leg.destination_name}: {leg.duration_human}")
```

### 3.5 Deep Links

| App | URL-Schema | Plattform |
|---|---|---|
| Google Maps (Web) | `https://www.google.com/maps/dir/?api=1&origin=...&destination=...&travelmode=transit` | Alle |
| Google Maps (App) | `comgooglemaps://?saddr=...&daddr=...&directionsmode=transit` | iOS |
| DB Navigator | `https://reiseauskunft.bahn.de/bin/query.exe/dn?S=...&Z=...&date=...&time=...` | Web+App |
| Apple Maps | `https://maps.apple.com/?saddr=...&daddr=...&dirflg=r` | iOS/macOS |
| BVG Fahrinfo | `https://fahrinfo.bvg.de/Fahrinfo/bin/query.bin/dn?from=...&to=...` | Web |

---

## 4. Calendar-Tool — Detaildesign

### 4.1 Architektur-Entscheidung

**Google Calendar API = einziger Write-Target.**

Sync-Kette: Google Calendar API → Notion Calendar (near-realtime) → Apple Calendar (15-20 Min Polling)

Voraussetzung: Apple Calendar und Notion Calendar sind mit demselben Google-Konto verbunden (nicht URL-Subscription, sondern Account-Integration).

### 4.2 CLI Interface

```bash
kit cal add <title> [OPTIONS]

Optionen:
  --start, -s       Startzeit (HH:MM)                        [ohne: Ganztages-Event]
  --date            Datum (YYYY-MM-DD oder "morgen", "freitag") [default: heute]
  --duration        Dauer (z.B. "1h", "30m")                [default: 1h]
  --location, -l    Ort
  --route-from      Route von diesem Ort berechnen und als Travel-Buffer eintragen
  --route-to        Route zu diesem Ort nach dem Termin
  --description     Beschreibung
  --calendar        Kalender-Name                            [default: primary]
  --json            JSON-Output

kit cal today                   # Heutige Termine anzeigen
kit cal tomorrow                # Morgen
kit cal week                    # Diese Woche
```

Relative Datumsangaben: `heute`, `morgen`, `uebermorgen`, Wochentage (`montag`-`sonntag`), `naechsten montag`. Parsing via `dateparser` mit deutscher Locale.

Ohne `--start` wird ein Ganztages-Event erstellt. MCP und CLI verwenden beide `start` als Feldname fuer Konsistenz.

### 4.3 Route-Integration

```bash
# Termin mit automatischem Reise-Puffer
kit cal add "Dinner bei Luigi" --at 19:00 --location "Luigi, Oranienstr 42" --route-from home

# Erzeugt ZWEI Kalender-Eintraege:
# 1. "🚇 Anreise: Dinner bei Luigi" 18:30-18:55 (Transit, 20 min + 5 min Puffer)
#    Beschreibung: Google Maps Link + DB Navigator Link
#    Farbe: Grau (automatisch, zur Unterscheidung von echten Terminen)
# 2. "Dinner bei Luigi" 19:00-20:00
#    Location: Luigi, Oranienstr 42
#
# Travel Buffer: 5 Min Puffer standardmaessig (konfigurierbar via --buffer)
# Wenn Route-Berechnung fehlschlaegt: Event wird trotzdem erstellt, ohne Buffer + Warnung
```

### 4.4 Python API

```python
from kit.cal import add_event, CalendarEvent
from kit.route import plan_route

# Event mit Route
event = CalendarEvent(
    title="Dinner bei Luigi",
    start="2026-03-25T19:00:00",
    duration_minutes=60,
    location="Luigi, Oranienstr 42, Berlin",
)
route = plan_route("home", event.location, mode="transit", arrive_by="19:00")

# Erstellt Termin + Travel-Buffer
add_event(event, travel_buffer=route)
```

---

## 5. Multi-Stop Tagesplanung (Agent Use Case)

Das Killer-Feature fuer Agent-Nutzung: Claude kann einen ganzen Tag planen.

```python
from kit.route import plan_day

plan = plan_day(
    start_location="home",
    stops=[
        {"name": "Metro einkaufen", "location": "Metro Friedrichshain", "duration": "30m", "earliest": "17:00"},
        {"name": "Besorgung", "location": "Kurfuerstendamm 42", "duration": "45m"},
        {"name": "Dinner", "location": "Luigi, Oranienstr 42", "duration": "2h", "fixed_time": "19:30"},
    ],
    end_location="home",
    mode="transit",
)
# name = Anzeigename fuer Kalender, location = Adresse/Koordinaten fuer Routing
# plan_day nutzt intern plan_multi_route fuer die Routing-Legs

# plan.is_feasible → True/False
# plan.total_travel_time → "1h 12min"
# plan.schedule → chronologische Liste mit Zeiten
# plan.warnings → ["Knapp: nur 8 Min zwischen Metro und City West"]
```

---

## 6. Setup-Flow

```bash
$ kit setup

Welcome to kit! Let's get you set up.

1/3 — Google Maps API Key
   You need a Google Maps API key with Directions API enabled.
   → Get one at: https://console.cloud.google.com/apis/credentials
   → Enable: Directions API, Geocoding API
   → Paste your key: AIza________________

2/3 — Google Calendar
   We'll open a browser for OAuth authentication.
   → Press Enter to continue...
   [Browser oeffnet sich fuer Google OAuth]
   ✓ Connected to calendar: paul@gmail.com

3/3 — Home Address
   Your default starting point for routes.
   → Enter your home address: Beispielstr 42, 10999 Berlin
   ✓ Verified: Beispielstraße 42, 10999 Berlin, Germany

Setup complete! Try: kit route home "Alexanderplatz"
```

---

## 7. Testing-Strategie

### 7.1 Test-Pyramide

| Ebene | Was | Wie |
|---|---|---|
| Unit Tests | Koordinaten-Parsing, Deep-Link-Generation, Output-Formatting | pytest, keine API-Calls |
| Integration Tests | Google Maps API, Google Calendar API | pytest-vcr (aufgezeichnete Responses) |
| CLI Tests | End-to-End CLI-Aufrufe | typer.testing.CliRunner |
| Smoke Tests | Echte API-Calls (manuell, nicht in CI) | pytest -m smoke |

### 7.2 VCR-Strategie (API-Mocking)

Erste echte API-Calls werden aufgezeichnet als YAML-Cassettes. Danach laufen Tests offline gegen aufgezeichnete Responses. Neue Routen/Szenarien: `pytest --vcr-record=new_episodes`.

### 7.3 Coverage-Ziel

≥ 90% fuer core.py, geo.py, deep_links.py, formatting.py. CLI-Tests decken Happy Path + Error Cases ab.

---

## 8. CLI-Features (Professional Grade)

- `--help` auf jedem Level (kit --help, kit route --help)
- `--version` zeigt Version
- `--json` fuer maschinenlesbaren Output
- `--verbose / -v` fuer Debug-Infos
- `--no-color` fuer Pipe-Kompatibilitaet
- Fehler als stderr, Ergebnisse als stdout
- Exit Codes: 0 = OK, 1 = User Error, 2 = API Error
- Shell-Completion (Typer generiert bash/zsh/fish completions)
- `kit config show` zeigt aktuelle Config
- `kit config set <key> <value>` aendert Config

### 8.1 Error Handling

**Exception-Hierarchie:**
```python
class KitError(Exception): pass
class ConfigError(KitError): pass       # Fehlende Config, ungueltige Keys
class RouteNotFoundError(KitError): pass # Keine Route gefunden
class GeocodingError(KitError): pass     # Adresse nicht aufloesbar
class APIError(KitError): pass           # Google API Fehler (Rate Limit, Auth, etc.)
class CalendarError(KitError): pass      # Calendar API Fehler
```

**Mapping auf Interfaces:**

| Exception | CLI Exit Code | MCP Response | Python API |
|---|---|---|---|
| ConfigError | 1 (User Error) | `isError: true` + Hinweis auf `kit setup` | raise ConfigError |
| RouteNotFoundError | 1 | `isError: true` + Alternativen vorschlagen | raise RouteNotFoundError |
| GeocodingError | 1 | `isError: true` + "Adresse nicht gefunden" | raise GeocodingError |
| APIError (429) | 2 (API Error) | `isError: true` + Retry-After Header | raise APIError, automatischer Backoff |
| APIError (auth) | 2 | `isError: true` + "kit setup --reauth" | raise APIError |
| Netzwerk-Timeout | 2 | `isError: true` + "Netzwerk nicht erreichbar" | raise APIError |

**Verhalten bei Teilfehlern:**
- `kit_cal_add` mit `route_from`: Wenn Route-Berechnung fehlschlaegt, wird der Kalender-Event trotzdem erstellt (ohne Travel-Buffer) + Warnung
- `kit_plan_day`: Wenn eine einzelne Leg fehlschlaegt, wird der Rest trotzdem berechnet + Warnung fuer die fehlende Leg

### 8.2 Caching und Rate Limiting

- **Response Cache**: Gleiche Route (origin + destination + mode) wird 15 Min gecacht (lokaler Disk-Cache in `~/.cache/kit/`)
- **Rate Limiting**: Automatischer exponentieller Backoff bei 429-Responses (1s, 2s, 4s, max 3 Retries)
- **Usage Tracking**: `kit config show-usage` zeigt API-Calls diesen Monat (Google Maps gibt 200$/Monat Free Credit ≈ 40.000 Directions-Requests)

---

## 9. MCP Server — Agent-Native Interface

### 9.1 Architektur

Der MCP Server ist das primaere Agent-Interface. Er exponiert alle kit-Tools als MCP-Tools die Claude Code direkt aufrufen kann — kein Bash-Umweg, strukturierter Input/Output, native Tool-Beschreibungen.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Code    │────▶│  kit MCP Server  │────▶│  Google Maps    │
│  (Agent)        │◀────│  (stdio)         │────▶│  Google Calendar│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                         src/kit/
                        ├── route/core.py    (shared logic)
                        ├── cal/core.py      (shared logic)
                              │
┌─────────────────┐     ┌──────────────────┐
│  Terminal       │────▶│  kit CLI         │──── gleiche Core-Logik
│  (Mensch)       │◀────│  (Typer)         │
└─────────────────┘     └──────────────────┘
```

CLI, Python API und MCP Server teilen sich dieselbe Core-Logik. Kein Code wird dupliziert.

### 9.2 MCP Tool-Definitionen

**kit_route** — Berechnet Routen zwischen zwei Orten:
```json
{
  "name": "kit_route",
  "description": "Calculate a route between two locations using Google Maps. Returns duration, steps, and deep links to navigation apps. Supports addresses, coordinates (lat,lng), and saved locations like 'home'.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "origin": {
        "type": "string",
        "description": "Start location: address, 'lat,lng' coordinates, or saved location name"
      },
      "destination": {
        "type": "string",
        "description": "End location: address, 'lat,lng' coordinates, or saved location name"
      },
      "mode": {
        "type": "string",
        "enum": ["transit", "walking", "bicycling", "driving"],
        "default": "transit"
      },
      "departure_time": {
        "type": "string",
        "description": "Departure time as HH:MM or ISO-8601. Default: now"
      },
      "arrival_time": {
        "type": "string",
        "description": "Desired arrival time as HH:MM or ISO-8601"
      }
    },
    "required": ["origin", "destination"]
  }
}
```

**kit_route_multi** — Berechnet Multi-Stop-Routen:
```json
{
  "name": "kit_route_multi",
  "description": "Calculate routes between multiple stops in sequence. Returns total travel time and per-leg details.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "stops": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Ordered list of locations to visit"
      },
      "mode": { "type": "string", "default": "transit" },
      "departure_time": { "type": "string" }
    },
    "required": ["stops"]
  }
}
```

**kit_cal_add** — Erstellt Kalender-Event mit optionalem Reise-Puffer:
```json
{
  "name": "kit_cal_add",
  "description": "Create a Google Calendar event. Syncs automatically to Notion Calendar and Apple Calendar. Can calculate and add a travel buffer event with navigation deep links.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": { "type": "string" },
      "start": { "type": "string", "description": "Start time as HH:MM or ISO-8601" },
      "date": { "type": "string", "description": "Date as YYYY-MM-DD or relative ('morgen', 'freitag'). Default: today" },
      "duration_minutes": { "type": "integer", "default": 60 },
      "location": { "type": "string" },
      "description": { "type": "string" },
      "route_from": { "type": "string", "description": "Calculate transit route FROM this location and add travel buffer event" },
      "route_to": { "type": "string", "description": "Calculate transit route TO this location after the event" },
      "calendar_id": { "type": "string", "default": "primary" }
    },
    "required": ["title", "start"]
  }
}
```

**kit_cal_list** — Listet Kalender-Events:
```json
{
  "name": "kit_cal_list",
  "description": "List calendar events for a given time range.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "range": {
        "type": "string",
        "enum": ["today", "tomorrow", "week", "custom"],
        "default": "today"
      },
      "start_date": { "type": "string" },
      "end_date": { "type": "string" }
    }
  }
}
```

**kit_plan_day** — Plant einen ganzen Tag mit Feasibility-Check:
```json
{
  "name": "kit_plan_day",
  "description": "Plan a full day with multiple stops. Calculates routes between all stops, checks if the schedule is feasible, and returns warnings for tight connections. Can create all calendar events at once.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "start_location": { "type": "string", "default": "home" },
      "end_location": { "type": "string", "default": "home" },
      "stops": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "location": { "type": "string" },
            "duration": { "type": "string", "description": "e.g. '30m', '1h', '2h'" },
            "fixed_time": { "type": "string", "description": "Fixed start time if not flexible" },
            "earliest": { "type": "string", "description": "Earliest possible start" }
          },
          "required": ["name"]
        }
      },
      "mode": { "type": "string", "default": "transit" },
      "create_events": { "type": "boolean", "default": false, "description": "If true, create all calendar events including travel buffers" }
    },
    "required": ["stops"]
  }
}
```

### 9.3 Claude Code Integration

Registration in `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "kit": {
      "command": "kit-mcp",
      "args": [],
      "description": "Personal toolbox: routing, calendar, day planning"
    }
  }
}
```

Nach Installation sieht Claude Code automatisch alle kit-Tools und kann sie direkt aufrufen:
```
Claude: "Du hast heute um 19:30 Dinner bei Luigi. Lass mich die Route berechnen."
→ ruft kit_route(origin="home", destination="Luigi, Oranienstr 42", mode="transit", arrival_time="19:30") auf
→ "Transit, 22 Min. Du musst um 19:08 los. Soll ich einen Reise-Puffer im Kalender eintragen?"
→ ruft kit_cal_add(title="Dinner bei Luigi", start="19:30", location="Luigi, Oranienstr 42", route_from="home") auf
```

### 9.4 MCP Server Implementierung

```python
# src/kit/mcp_server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from kit.route.mcp_tools import register_route_tools
from kit.cal.mcp_tools import register_cal_tools
from kit.config import load_config

server = Server("kit")

async def main():
    config = load_config()
    register_route_tools(server, config)
    register_cal_tools(server, config)

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

def run():
    """Entry-point fuer pyproject.toml — startet den async Server."""
    asyncio.run(main())
```

Entry-Point in `pyproject.toml`:
```toml
[project.scripts]
kit = "kit.cli:app"
kit-mcp = "kit.mcp_server:run"
```

---

## 10. Zukunft (nicht im ersten Build)

Diese Features sind notiert fuer spaetere Iterationen:

- **Alternative Routing-Backends**: MOTIS (Open Source), HaFAS/DB-API, OSRM
- **Notion-Datenbank-Sync**: Tasks mit Deadlines als Kalender-Events
- **Fahrrad-Routing**: Openrouteservice fuer Berlin-optimierte Radrouten
- **Wetter-Integration**: Warnung bei Regen wenn Fahrrad/Fuss geplant
- **Kosten-Tracking**: Google Maps API Usage Monitor
- **Weitere Tools unter kit**: `kit finance`, `kit scrape`, `kit notify`

---

## 11. Nicht-Ziele (explizit ausgeschlossen)

- Kein eigener Routing-Server (wir nutzen Google Maps API)
- Keine UI / Web-App (rein CLI + Python API)
- Kein Real-Time Tracking (nur Planung)
- Keine Kalender-Sync-Engine (Google Calendar ist die Source of Truth)
- Keine Multi-User-Features
