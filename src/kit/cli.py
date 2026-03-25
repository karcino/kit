"""Kit CLI — Typer app with subcommand routing."""

import typer

app = typer.Typer(
    name="kit",
    help="Agentic-ready personal CLI toolbox.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Kit — Agentic-ready personal CLI toolbox."""
    if ctx.invoked_subcommand is None:
        raise typer.Exit()


if __name__ == "__main__":
    app()
