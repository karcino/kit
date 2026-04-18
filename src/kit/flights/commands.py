"""CLI commands for kit flights."""

from __future__ import annotations

from datetime import date

import typer
from rich.console import Console
from rich.table import Table
from typer.core import TyperGroup

from kit.errors import KitError
from kit.flights.core import FlightSearch, FlightSearchResult
from kit.flights.planner import search_flights

console = Console(stderr=True)
stdout = Console()


class _DefaultToSearchGroup(TyperGroup):
    """TyperGroup that falls through to `search` when no subcommand matches."""

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["search"] + args
        return super().parse_args(ctx, args)


flights_app = typer.Typer(
    help="Cheapest Ryanair fares in a date window.",
    cls=_DefaultToSearchGroup,
)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date {value!r}; use YYYY-MM-DD.") from exc


@flights_app.command(name="search")
def flights_search(
    origin: str = typer.Argument(..., help="Origin IATA code (e.g. BER) or airport name"),
    destination: str = typer.Argument(..., help="Destination IATA code or airport name"),
    date_from: str = typer.Option(..., "--from", "-f", help="Earliest departure (YYYY-MM-DD)"),
    date_to: str = typer.Option(..., "--to", "-t", help="Latest return date (round-trip) or latest departure (one-way)"),
    round_trip: bool = typer.Option(False, "--round-trip", "-r", help="Search round-trip flights"),
    nights_min: int | None = typer.Option(None, "--nights-min", help="Round-trip: min nights (ignored unless --round-trip)"),
    nights_max: int | None = typer.Option(None, "--nights-max", help="Round-trip: max nights (ignored unless --round-trip)"),
    max_results: int = typer.Option(20, "--max", "-n", help="Max number of options to return"),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
    add: int | None = typer.Option(None, "--add", help="1-based index of a result to add to Google Calendar"),
) -> None:
    """Search for cheapest Ryanair flights in a date window."""
    query = FlightSearch(
        origin=origin,
        destination=destination,
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        trip_type="round_trip" if round_trip else "one_way",
        nights_min=nights_min,
        nights_max=nights_max,
        max_results=max_results,
    )

    try:
        result = search_flights(query)
    except KitError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(2) from exc

    if output_json:
        typer.echo(result.model_dump_json(indent=2))
    else:
        _render_table(result)

    if add is not None:
        _add_to_calendar(result, add)


def _add_to_calendar(result: FlightSearchResult, index: int) -> None:
    """Convert result.options[index-1] to a calendar event and create it."""
    if not (1 <= index <= len(result.options)):
        console.print(
            f"[red]--add {index} out of range (have {len(result.options)} results).[/red]"
        )
        raise typer.Exit(2)

    opt = result.options[index - 1]
    candidate = opt.as_calendar_event_candidate()
    event = candidate.to_calendar_event()

    # Lazy imports so flights CLI doesn't pay cal import cost on plain searches.
    from kit.cal.google_cal import GoogleCalendarClient
    from kit.errors import CalendarError

    try:
        client = GoogleCalendarClient()
        ev_result = client.add_event(event)
    except CalendarError as exc:
        console.print(f"[red]Calendar error: {exc}[/red]")
        if "auth" in str(exc).lower() or "authenticated" in str(exc).lower():
            console.print("[yellow]Hint: run `kit cal auth` first.[/yellow]")
        raise typer.Exit(2) from exc
    except KitError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(2) from exc

    ev_id = ev_result.get("id") if isinstance(ev_result, dict) else None
    console.print(
        f"[bold green]Added to calendar:[/bold green] {event.title} "
        f"({event.start:%Y-%m-%d %H:%M}) — id={ev_id}"
    )


def _render_table(result: FlightSearchResult) -> None:
    if not result.options:
        console.print("[yellow]No flights found.[/yellow]")
        return

    table = Table(title=f"Ryanair: {result.query.origin} → {result.query.destination}")
    table.add_column("Departure", style="cyan")
    if result.query.trip_type == "round_trip":
        table.add_column("Return", style="cyan")
    table.add_column("Price", justify="right", style="green")

    for opt in result.options:
        row = [opt.departure.strftime("%Y-%m-%d %H:%M")]
        if result.query.trip_type == "round_trip":
            ret = opt.return_departure
            row.append(ret.strftime("%Y-%m-%d %H:%M") if ret else "—")
        row.append(f"{opt.price:.2f} {opt.currency}")
        table.add_row(*row)

    stdout.print(table)

    if result.cheapest:
        c = result.cheapest
        console.print(
            f"[bold green]Cheapest:[/bold green] {c.price:.2f} {c.currency} "
            f"on {c.departure:%Y-%m-%d}"
        )
