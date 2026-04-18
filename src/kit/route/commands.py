"""CLI commands for kit route."""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

import typer
from typer.core import TyperGroup
from rich.console import Console

from kit.errors import KitError
from kit.route.core import TransportMode
from kit.route.planner import plan_route, plan_multi_route
from kit.utils.formatting import print_route, print_route_json

console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Custom Typer group that defaults to "plan" when no subcommand matches.
# This allows `kit route "A" "B"` in addition to `kit route plan "A" "B"`.
# ---------------------------------------------------------------------------

class _DefaultToPlanGroup(TyperGroup):
    """A TyperGroup that falls through to the 'plan' subcommand
    when the first argument isn't a known subcommand."""

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["plan"] + args
        return super().parse_args(ctx, args)


route_app = typer.Typer(
    help="Route planning between locations.",
    cls=_DefaultToPlanGroup,
)


def _parse_time(value: str) -> datetime:
    """Parse a time string (HH:MM or ISO-8601) into a datetime."""
    if "T" in value or ("-" in value and len(value) > 5):
        return datetime.fromisoformat(value)

    try:
        hour, minute = value.split(":")
        now = datetime.now()
        return now.replace(
            hour=int(hour), minute=int(minute), second=0, microsecond=0,
        )
    except (ValueError, AttributeError):
        raise typer.BadParameter(f"Invalid time format: {value!r}. Use HH:MM or ISO-8601.")


@route_app.command(name="plan")
def route_plan(
    origin: str = typer.Argument(..., help="Start: address, lat,lng, or 'home'"),
    destination: str = typer.Argument(..., help="End: address, lat,lng, or 'home'"),
    mode: TransportMode = typer.Option(TransportMode.TRANSIT, "--mode", "-m", help="Transport mode"),
    depart: Optional[str] = typer.Option(None, "--depart", "-d", help="Departure HH:MM or ISO-8601"),
    arrive: Optional[str] = typer.Option(None, "--arrive", "-a", help="Arrival HH:MM or ISO-8601"),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
) -> None:
    """Calculate a route between two locations."""
    if depart and arrive:
        console.print("[red]Error: --depart and --arrive are mutually exclusive[/red]")
        raise typer.Exit(1)

    kwargs: dict = {"mode": mode}
    if depart:
        kwargs["departure"] = _parse_time(depart)
    if arrive:
        kwargs["arrival"] = _parse_time(arrive)

    try:
        result = plan_route(origin, destination, **kwargs)
    except KitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)

    if output_json:
        typer.echo(print_route_json(result))
    else:
        print_route(result)


@route_app.command(name="multi")
def route_multi(
    stops: List[str] = typer.Argument(..., help="Two or more locations"),
    mode: TransportMode = typer.Option(TransportMode.TRANSIT, "--mode", "-m", help="Transport mode"),
    depart: Optional[str] = typer.Option(None, "--depart", "-d", help="Departure HH:MM or ISO-8601"),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
) -> None:
    """Plan a multi-stop route (A -> B -> C)."""
    if len(stops) < 2:
        console.print("[red]Error: multi-stop route requires at least 2 stops[/red]")
        raise typer.Exit(1)

    kwargs: dict = {"mode": mode}
    if depart:
        kwargs["departure"] = _parse_time(depart)

    try:
        results = plan_multi_route(stops, **kwargs)
    except KitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(2)

    if output_json:
        data = [json.loads(print_route_json(r)) for r in results]
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print_route(r)
