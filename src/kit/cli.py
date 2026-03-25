"""Kit CLI — Typer app with subcommand routing."""

from __future__ import annotations

import typer

from kit import __version__
from kit.route.commands import route_app
from kit.setup_cmd import setup

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
app.command()(setup)


if __name__ == "__main__":
    app()
