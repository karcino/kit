"""CLI commands for kit cal."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import typer
from rich.console import Console
from rich.table import Table

from kit.cal.core import CalendarEvent, TravelBuffer
from kit.cal.google_cal import GoogleCalendarClient
from kit.errors import KitError
from kit.route.planner import plan_route

cal_app = typer.Typer(help="Calendar management.", no_args_is_help=True)
console = Console(stderr=True)

# CET timezone (Europe/Berlin base)
_CET = timezone(timedelta(hours=1))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_duration(duration_str: str) -> int:
    """Parse duration string like '1h', '90m', '90' into minutes."""
    duration_str = duration_str.strip().lower()
    if duration_str.endswith("h"):
        return int(float(duration_str[:-1]) * 60)
    if duration_str.endswith("m"):
        return int(duration_str[:-1])
    return int(duration_str)


def _date_range(target_date) -> tuple[str, str]:
    """Return (time_min, time_max) ISO strings for a given date."""
    start = datetime(target_date.year, target_date.month, target_date.day,
                     0, 0, 0, tzinfo=_CET)
    end = datetime(target_date.year, target_date.month, target_date.day,
                   23, 59, 59, tzinfo=_CET)
    return start.isoformat(), end.isoformat()


def _render_events(events: list[dict], label: str) -> None:
    """Render events as a Rich table."""
    if not events:
        Console().print("[dim]No events.[/dim]")
        return
    table = Table(title=f"Events ({label})")
    table.add_column("Time", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Location", style="dim")
    for ev in events:
        start_raw = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", ""))
        if "T" in start_raw:
            display_time = start_raw[11:16]
        else:
            display_time = start_raw  # all-day: show date
        table.add_row(display_time, ev.get("summary", ""), ev.get("location", ""))
    Console().print(table)


# ---------------------------------------------------------------------------
# cal add
# ---------------------------------------------------------------------------

@cal_app.command()
def add(
    title: str = typer.Argument(..., help="Event title"),
    at: str | None = typer.Option(None, "--at", "-a", help="Start time HH:MM"),
    duration: str = typer.Option("60", "--duration", "-d", help="Duration in minutes (or e.g. 1h, 90m)"),
    location: str | None = typer.Option(None, "--location", "-l", help="Event location"),
    route_from: str | None = typer.Option(None, "--route-from", help="Add travel buffer from location"),
    description: str | None = typer.Option(None, "--description", help="Event description"),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
) -> None:
    """Create a calendar event."""
    try:
        event_date = datetime.now().date()

        if at:
            h, m = int(at.split(":")[0]), int(at.split(":")[1])
            start_dt = datetime(event_date.year, event_date.month, event_date.day,
                                h, m, tzinfo=_CET)
            event = CalendarEvent(
                title=title,
                start=start_dt,
                duration_minutes=_parse_duration(duration),
                location=location,
                description=description,
            )
        else:
            event = CalendarEvent(
                title=title,
                all_day=True,
                date=str(event_date),
                location=location,
                description=description,
            )

        client = GoogleCalendarClient()

        # Travel buffer (only when we have a start time and route_from)
        if route_from and at:
            try:
                dest = location or title
                route_result = plan_route(route_from, dest, mode="transit")
                buffer_minutes = 5
                travel_end = start_dt - timedelta(minutes=buffer_minutes)
                travel_start = travel_end - timedelta(seconds=route_result.duration_seconds)
                links = f"Google Maps: {route_result.deep_links.google_maps}"
                if route_result.deep_links.db_navigator:
                    links += f"\nDB Navigator: {route_result.deep_links.db_navigator}"
                buffer = TravelBuffer(
                    title=f"Anreise: {title}",
                    start=travel_start,
                    end=travel_end,
                    description=(
                        f"{route_result.duration_human} \u00b7 {route_result.mode.value}\n{links}"
                    ),
                )
                client.add_travel_buffer(buffer)
                console.print(
                    f"[green]\u2713 Travel buffer: "
                    f"{travel_start.strftime('%H:%M')}-{travel_end.strftime('%H:%M')}[/green]"
                )
            except KitError as e:
                console.print(
                    f"[yellow]\u26a0 Route failed: {e}. Event created without buffer.[/yellow]"
                )

        result = client.add_event(event)

        if output_json:
            print(json.dumps(result, indent=2, default=str))
        else:
            console.print(f"[green]\u2713 Event created: {title}[/green]")

    except KitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# cal today / cal tomorrow
# ---------------------------------------------------------------------------

@cal_app.command()
def today(
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
) -> None:
    """Show today's events."""
    _list_for_date(datetime.now().date(), "today", output_json)


@cal_app.command()
def tomorrow(
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
) -> None:
    """Show tomorrow's events."""
    tmrw = datetime.now().date() + timedelta(days=1)
    _list_for_date(tmrw, "tomorrow", output_json)


# ---------------------------------------------------------------------------
# cal list
# ---------------------------------------------------------------------------

@cal_app.command(name="list")
def list_events(
    date: str | None = typer.Option(None, "--date", help="Date YYYY-MM-DD (default: today)"),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
) -> None:
    """List events for a specific date."""
    if date:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target = datetime.now().date()

    _list_for_date(target, str(target), output_json)


# ---------------------------------------------------------------------------
# cal delete
# ---------------------------------------------------------------------------

@cal_app.command()
def delete(
    event_id: str = typer.Argument(..., help="Event ID to delete"),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
) -> None:
    """Delete a calendar event by ID."""
    try:
        client = GoogleCalendarClient()
        client.delete_event(event_id)

        if output_json:
            print(json.dumps({"deleted": event_id, "status": "ok"}, indent=2))
        else:
            console.print(f"[green]\u2713 Deleted event: {event_id}[/green]")

    except KitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# Shared list helper
# ---------------------------------------------------------------------------

def _list_for_date(target_date, label: str, output_json: bool) -> None:
    """Fetch and display events for a single date."""
    time_min, time_max = _date_range(target_date)
    try:
        client = GoogleCalendarClient()
        events = client.list_events(time_min=time_min, time_max=time_max)

        if output_json:
            print(json.dumps(events, indent=2, default=str))
        else:
            _render_events(events, label)

    except KitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)
