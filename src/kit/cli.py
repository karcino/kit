"""Kit CLI — Typer app with subcommand routing."""

from __future__ import annotations

import typer

from kit import __version__
from kit.cal.commands import cal_app
from kit.docs.commands import docs_app
from kit.flights.commands import flights_app
from kit.pdf.commands import pdf_app
from kit.route.commands import route_app
from kit.plan_day_cmd import plan_day_cmd
from kit.setup_cmd import setup
from kit.youtube.commands import youtube_app

app = typer.Typer(
    name="kit",
    help="Agentic-ready personal CLI toolbox.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"kit {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Kit — Agentic-ready personal CLI toolbox."""


app.add_typer(route_app, name="route")
app.add_typer(cal_app, name="cal")
app.add_typer(docs_app, name="docs")
app.add_typer(flights_app, name="flights")
app.add_typer(pdf_app, name="pdf")
app.add_typer(youtube_app, name="youtube")
app.command()(setup)
app.command(name="plan-day")(plan_day_cmd)


if __name__ == "__main__":
    app()
