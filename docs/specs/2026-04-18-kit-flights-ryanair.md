# Kit Flights — Ryanair Best-Price Search

**Date:** 2026-04-18 (refactored from Apify to direct Ryanair API)
**Status:** Shipped, verified with live data (BER→DUB one-way + round-trip).
**Author:** Paul Fiedler + Claude

---

## 1. Vision

Find the cheapest Ryanair flight between two airports inside a date window. Three interfaces (CLI / Python API / MCP tool), matching the `route` and `cal` pattern.

```bash
kit flights search BER DUB --from 2026-05-01 --to 2026-05-10
kit flights search BER DUB --from 2026-05-01 --to 2026-05-30 \
  --round-trip --nights-min 3 --nights-max 7
kit flights search BER DUB --from 2026-05-01 --to 2026-05-10 --json
```

---

## 2. Architecture

```
src/kit/flights/
├── __init__.py        # re-exports
├── core.py            # FlightSearch, FlightOption, FlightSearchResult (Pydantic)
├── ryanair.py         # RyanairFareClient — httpx wrapper on public API
├── planner.py         # search_flights() — sorts, picks cheapest
├── commands.py        # flights_app with `search` subcommand
└── mcp_tools.py       # kit_flight_search MCP tool
```

Mirrors `route/` and `cal/`. No auth, no subscription, no config field — Ryanair's public fare API is unauthenticated.

## 3. Transport: Ryanair public fare API

Uses the same endpoints ryanair.com calls from its own booking UI.

**One-way (per month):**
```
GET https://www.ryanair.com/api/farfnd/v4/oneWayFares/{origin}/{destination}/cheapestPerDay
    ?outboundMonthOfDate={YYYY-MM-DD}
```
Returns one fare per day of the requested month. Client loops per month when the query spans multiple.

**Round-trip:** Same plus the round-trip endpoint gives an independent `inbound` list. The client pairs outbound × inbound days, filters by `nights_min`/`nights_max`, and sums the prices.

**Only requirement:** a browser-like User-Agent (API 403s without one).

Errors map to `FlightSearchError` (timeout, non-JSON) or `APIError` (HTTP ≥ 400).

## 4. Data model

```python
FlightSearch   # origin/destination IATA, date window, trip_type, nights_min/max, max_results
FlightOption   # departure datetime, optional return_departure, price, currency, booking_url
FlightSearchResult  # query + sorted options + cheapest + searched_at + source="ryanair"
```

`booking_url` is synthesized client-side — the API doesn't return one:
```
https://www.ryanair.com/gb/en/trip/flights/select?adults=1&dateOut={day}&originIata={iata}&destinationIata={iata}
```

## 5. Verified end-to-end

```
$ kit flights search BER DUB --from 2026-05-01 --to 2026-05-10
Cheapest: 26.99 EUR on 2026-05-07

$ kit flights search BER DUB --from 2026-05-01 --to 2026-05-30 --round-trip --nights-min 3 --nights-max 7
Cheapest round-trip: 43.98 EUR (May 7 → May 12, 5 nights)
```

Tests: 210/210 pass (`pytest -m "not smoke"`).

## 6. Out of scope (v1)

- **Calendar integration** — add found flight as event. Blocked on `2026-04-18-cross-tool-integration-hooks.md`.
- **Day-planner integration** — flight as a stop with airport transfer + check-in buffer.
- **Price alerts** — use `kit watch` (future); flights could later register a watch-job.
- **Other airlines** — actor is Ryanair-only. EasyJet/Wizzair would be sibling modules.
- **Booking automation** — explicit non-goal.

## 7. History

- First draft: wrapped Apify's `saswave/ryanair-best-price-scraper` actor via sync-run endpoint. Required an Apify API token and a rented paid actor.
- Refactored 2026-04-18: switched to Ryanair's public fare API (no auth, no subscription). Actor was paid-only; direct API is free.
