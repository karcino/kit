"""CLI commands for kit youtube."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from typer.core import TyperGroup

from kit.errors import KitError
from kit.youtube.core import TranscriptRequest, TranscriptResult
from kit.youtube.planner import fetch_transcript

console = Console(stderr=True)
stdout = Console()


class _DefaultToTranscriptGroup(TyperGroup):
    """TyperGroup that falls through to `transcript` when no subcommand matches."""

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["transcript"] + args
        return super().parse_args(ctx, args)


youtube_app = typer.Typer(
    help="Fetch YouTube video transcripts (no API key required).",
    cls=_DefaultToTranscriptGroup,
)


@youtube_app.command(name="transcript")
def youtube_transcript(
    source: str = typer.Argument(..., help="YouTube URL or 11-char video ID"),
    lang: str = typer.Option(
        "en",
        "--lang",
        "-l",
        help="Comma-separated language preference list (e.g. 'en,de').",
    ),
    no_generated: bool = typer.Option(
        False,
        "--no-generated",
        help="Reject auto-generated transcripts; fail if only generated exists.",
    ),
    output_json: bool = typer.Option(False, "--json", help="JSON output for agents"),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Plain text only, no timestamps (pipe-friendly).",
    ),
) -> None:
    """Fetch a transcript for a YouTube video."""
    languages = [code.strip() for code in lang.split(",") if code.strip()]
    if not languages:
        languages = ["en"]

    try:
        request = TranscriptRequest(
            source=source,
            languages=languages,
            allow_generated=not no_generated,
        )
        result = fetch_transcript(request)
    except (KitError, ValueError) as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(2) from exc

    if output_json:
        typer.echo(result.model_dump_json(indent=2))
        return

    if plain:
        typer.echo(result.plain_text)
        return

    _render_table(result)


def _render_table(result: TranscriptResult) -> None:
    header = (
        f"YouTube transcript — {result.video_id} "
        f"({result.language}{', auto' if result.is_generated else ''})"
    )

    if not result.segments:
        console.print(f"[yellow]{header} — empty transcript.[/yellow]")
        return

    table = Table(title=header)
    table.add_column("Time", style="cyan", no_wrap=True)
    table.add_column("Text")

    for seg in result.segments:
        table.add_row(_format_time(seg.start), seg.text)

    stdout.print(table)
    console.print(
        f"[dim]{len(result.segments)} segments · "
        f"{_format_time(result.total_duration)} total[/dim]"
    )


def _format_time(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
