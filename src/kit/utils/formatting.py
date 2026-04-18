"""Human-readable formatting for CLI output."""

from __future__ import annotations

from rich.console import Console

from kit.route.core import RouteResult


# ---------------------------------------------------------------------------
# Scalar formatters
# ---------------------------------------------------------------------------

def format_duration(seconds: int) -> str:
    """Format seconds into a human-readable duration string.

    Examples: ``"1h 30min"``, ``"45 min"``.
    """
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes}min"
    return f"{minutes} min"


def format_distance(meters: int) -> str:
    """Format meters into a human-readable distance string.

    Examples: ``"2.3 km"``, ``"450 m"``.
    """
    if meters >= 1000:
        return f"{meters / 1000:.1f} km"
    return f"{meters} m"


# ---------------------------------------------------------------------------
# Rich route display
# ---------------------------------------------------------------------------

def print_route(result: RouteResult, *, console: Console | None = None) -> None:
    """Print a formatted route summary to the terminal using Rich."""
    con = console or Console()

    con.print(
        f"\n[bold]{result.origin}[/bold] \u2192 [bold]{result.destination}[/bold]"
    )
    con.print(
        f"   {result.mode.value.title()} \u00b7 {result.duration_human} \u00b7 "
        f"Depart {(result.departure.astimezone() if result.departure.tzinfo else result.departure).strftime('%H:%M')} \u2192 "
        f"Arrive {(result.arrival.astimezone() if result.arrival.tzinfo else result.arrival).strftime('%H:%M')}\n"
    )

    for i, step in enumerate(result.steps, 1):
        parts = [f"   {i}. {step.instruction}"]
        if step.transit_line:
            parts.append(f" \u00b7 {step.transit_stops} stops")
        parts.append(f" \u00b7 {step.duration_human}")
        con.print("".join(parts))

    con.print()
    if result.deep_links.google_maps:
        con.print(f"   Google Maps: {result.deep_links.google_maps}")
    if result.deep_links.db_navigator:
        con.print(f"   DB Navigator: {result.deep_links.db_navigator}")
    if result.deep_links.apple_maps:
        con.print(f"   Apple Maps: {result.deep_links.apple_maps}")
    con.print()


# ---------------------------------------------------------------------------
# JSON output for agents / MCP
# ---------------------------------------------------------------------------

def print_route_json(result: RouteResult) -> str:
    """Return a JSON string of the route result, enriched with human fields.

    Intended for agent/MCP consumption where structured data is preferred.
    """
    data = result.model_dump(mode="json")
    data["duration_human"] = result.duration_human
    for i, step in enumerate(result.steps):
        data["steps"][i]["duration_human"] = step.duration_human
        data["steps"][i]["distance_human"] = format_distance(step.distance_meters)

    import json
    return json.dumps(data, indent=2, ensure_ascii=False)
