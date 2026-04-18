# Kit — Cross-Tool Integration Hooks (Open Architecture Question)

**Date:** 2026-04-18
**Resolved:** 2026-04-18
**Status:** Resolved — option (d) adopted, implemented in `kit.integrations`.
**Author:** Paul Fiedler (raised) + Claude (drafted + implemented)

---

## Context

Kit today has three tools: `route`, `cal`, `docs`. Two in-progress: `flights` (just added, v1 standalone), `watch` (spec'd, not built). More planned: `scrape`, `notify`, `finance`.

One pair has cross-tool integration: `cal` calls `route` to compute travel buffers. The integration is **hand-coded** — `src/kit/cal/google_cal.py` and `src/kit/route/planner.py` know about each other directly.

## The question

**How should new Kit tools expose integration hooks into existing tools (`cal`, `route`, `plan_day`) without each new tool re-inventing the integration layer?**

Without an answer, integration grows quadratically: N tools × M cross-tool scenarios = NM bespoke couplings. That breaks the "three interfaces, one core" clarity the `route`+`cal` pattern established.

Concrete scenarios blocked on this answer:
- `kit flights` → `kit cal`: add a found flight as a calendar event, with travel buffer to the airport via `kit route`.
- `kit flights` → `kit plan_day`: flights participate in day planning (check-in buffer, airport transfer as a leg).
- `kit watch` → `kit notify`: a price hit triggers a notification.
- `kit flights` → `kit watch`: register a recurring price check on a specific route/date.

## Why it matters now

`kit flights` was added without integration hooks **on purpose** — Paul's explicit instruction was "this is an architectural question that applies to every new tool, not Ryanair-specific. Don't bake a bespoke decision into flights just to unblock it."

So v1 of flights returns data only. The architectural decision is deferred until it can be made once, correctly, for all tools.

## Options to evaluate

**(a) Per-tool adapters.** Each tool exposes a `to_calendar_event() -> CalendarEventCandidate`, `to_route_stop() -> RouteStop`, etc. Simple, explicit, but O(N×M) methods — each new cross-tool scenario requires every existing tool to learn a new adapter.

**(b) Central `kit.integrations` module with contracts.** Tools declare what integration contracts they satisfy. `kit.integrations.CalendarEventProvider`, `kit.integrations.RouteableLocation`, etc. A new cross-tool scenario adds a contract, not methods on every tool.

**(c) `plan_day` as dispatcher, tools register as providers.** The day-planner becomes the integration hub. Other tools register providers (`flights` → `FlightProvider`, `cal` → `EventProvider`). `plan_day` orchestrates. Centralizes integration, but makes `plan_day` a god-object.

**(d) Pure Pydantic interchange.** Tool outputs conform to a shared `CalendarEventCandidate` / `RouteLeg` / `PriceHit` schema. No method-based coupling at all — tools just emit data that other tools can consume if they want. Most decoupled; requires strict schema governance.

## Decision: option (d) adopted

**Option (d) pure Pydantic interchange**, with a thin `kit.integrations` module (option b light). Rationale:

- Keeps tools fully decoupled — no tool imports another tool.
- `plan_day` stays lean — it consumes `CalendarEventCandidate` shapes, not raw module types.
- Leverages the Pydantic discipline already present in every tool.
- Lazy imports inside conversion methods prevent parse-time coupling.

**What was implemented (2026-04-18):**
- `src/kit/integrations.py` — defines `CalendarEventCandidate`, `RouteLeg`, `PriceHit`
- `FlightOption.as_calendar_event_candidate()` → `CalendarEventCandidate`
- `FlightOption.as_route_leg()` → `RouteLeg`
- `RouteResult.as_route_leg()` → `RouteLeg`

**Migration of `cal + route` (existing hand-coded coupling):**
The current `cal/mcp_tools.py` still imports `plan_route` directly (it works, leave it).
When extending cal to accept *any* source (flights, external APIs), use this pattern:
```python
# Instead of: from kit.flights import FlightOption
# Do: accept CalendarEventCandidate from the caller
from kit.integrations import CalendarEventCandidate

def kit_cal_add_from_candidate(candidate: CalendarEventCandidate) -> str:
    event = CalendarEvent(title=candidate.title, start=candidate.start, ...)
    ...
```

**Next actions remaining:**
- Wire `kit_cal_add_from_candidate` MCP tool (when Paul wants flights → cal flow)
- Apply `PriceHit` to `watch` module at build time (watch not yet built)

## Pointers

- `docs/specs/2026-03-25-kit-toolbox-design.md` — master toolbox design, section 2.1 for module layout.
- `docs/specs/2026-04-18-kit-flights-ryanair.md` — flights v1 spec; section 6 lists the deferred integrations.
- `docs/specs/2026-03-26-kit-watch-price-monitor.md` — watch spec; likely the second tool to need cross-tool hooks.
- `src/kit/cal/google_cal.py` and `src/kit/route/planner.py` — existing hand-coded integration.
