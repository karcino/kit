"""Top-level `kit plan-day` CLI command."""

from __future__ import annotations

import json as _json
from datetime import datetime

import dateparser
import typer
from rich.console import Console
from rich.table import Table

from kit.errors import KitError
from kit.route.planner import plan_day

_err = Console(stderr=True)
_out = Console()


def plan_day_cmd(
    tasks: list[str] = typer.Argument(
        ..., help="Tasks as 'Name' or 'Name @ Location' (one per arg).",
    ),
    date: str | None = typer.Option(
        None, "--date", "-d", help="Schedule date (ISO or natural language).",
    ),
    start_hour: int = typer.Option(9, "--start", help="Earliest hour (0-23)."),
    end_hour: int = typer.Option(18, "--end", help="Latest hour (0-23)."),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents."),
) -> None:
    """Build a sequential day schedule with travel times between located tasks."""
    schedule_date = dateparser.parse(date, languages=["de", "en"]).date() if date else None
    try:
        result = plan_day(
            tasks, schedule_date=schedule_date,
            start_hour=start_hour, end_hour=end_hour,
        )
    except KitError as exc:
        _err.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(2) from exc

    if output_json:
        typer.echo(_json.dumps(result, indent=2, ensure_ascii=False))
        return

    table = Table(title=f"Day plan — {result['date']}")
    table.add_column("Time", style="cyan", no_wrap=True)
    table.add_column("Task")
    table.add_column("Location", style="dim")
    table.add_column("Travel", style="magenta")
    for entry in result["schedule"]:
        travel = entry.get("travel")
        travel_str = f"+{travel['duration_human']}" if travel else ""
        table.add_row(entry["time"], entry["task"], entry.get("location") or "—", travel_str)
    _out.print(table)
