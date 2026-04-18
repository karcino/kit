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
    help="Find cheapest Ryanair flights via Apify.",
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
    date_to: str = typer.Option(..., "--to", "-t", help="Latest date to consider (YYYY-MM-DD)"),
    round_trip: bool = typer.Option(False, "--round-trip", "-r", help="Search round-trip flights"),
    nights_min: int | None = typer.Option(None, "--nights-min", help="Round-trip: min nights"),
    nights_max: int | None = typer.Option(None, "--nights-max", help="Round-trip: max nights"),
    max_results: int = typer.Option(20, "--max", "-n", help="Max number of options to return"),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
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


def _render_table(result: FlightSearchResult) -> None:
    if not result.options:
        console.print("[yellow]No flights found.[/yellow]")
        return

    table = Table(title=f"Ryanair: {result.query.origin} → {result.query.destination}")
    table.add_column("Departure", style="cyan")
    if result.query.trip_type == "round_trip":
        table.add_column("Return", style="cyan")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Flight", style="dim")

    for opt in result.options:
        row = [opt.departure.strftime("%Y-%m-%d %H:%M")]
        if result.query.trip_type == "round_trip":
            ret = opt.return_departure
            row.append(ret.strftime("%Y-%m-%d %H:%M") if ret else "—")
        row.append(f"{opt.price:.2f} {opt.currency}")
        row.append(opt.flight_number or "—")
        table.add_row(*row)

    stdout.print(table)

    if result.cheapest:
        c = result.cheapest
        console.print(
            f"[bold green]Cheapest:[/bold green] {c.price:.2f} {c.currency} "
            f"on {c.departure:%Y-%m-%d}"
        )
