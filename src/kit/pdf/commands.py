"""Typer CLI commands für kit pdf.

Commands:
- kit pdf extract URL_OR_PATH       — volle Text + Metadata, Markdown-Output
- kit pdf meta URL_OR_PATH          — nur Metadata, schneller
- kit pdf batch URLS_FILE [--out]   — mehrere PDFs aus einer Datei (eine URL/Pfad pro Zeile)
                                       Output: Konkatenierte Markdown-Datei
"""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kit.pdf.core import PDFInfo, extract_metadata, extract_text


pdf_app = typer.Typer(
    name="pdf",
    help="PDF text + metadata extraction for OSINT workflows.",
    no_args_is_help=True,
)


@pdf_app.command("extract")
def cmd_extract(
    source: str = typer.Argument(..., help="PDF-URL oder lokaler Pfad"),
    output: Path | None = typer.Option(None, "--out", "-o", help="Markdown-Output-Pfad. Default: stdout."),
    as_json: bool = typer.Option(False, "--json", help="JSON statt Markdown ausgeben."),
) -> None:
    """Lade ein PDF, extrahiere Text + Metadata, render als Markdown oder JSON."""
    console = Console(stderr=True)
    console.print(f"[dim]Lade {source}[/dim]")
    info = extract_text(source)
    console.print(f"[green]✓[/green] {info.num_pages} Seiten, {info.byte_size:,} Bytes, SHA {info.sha256[:12]}…")
    if as_json:
        content = json.dumps(info.to_dict(), indent=2, ensure_ascii=False)
    else:
        content = info.to_markdown()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        console.print(f"[dim]→ {output}[/dim]")
    else:
        typer.echo(content)


@pdf_app.command("meta")
def cmd_meta(
    source: str = typer.Argument(..., help="PDF-URL oder lokaler Pfad"),
) -> None:
    """Nur Metadaten (keine Text-Extraktion) — schnell."""
    console = Console()
    info = extract_metadata(source)
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    d = info.to_dict()
    for key in ("source", "num_pages", "title", "author", "creator", "producer", "creation_date", "byte_size", "sha256"):
        val = d.get(key)
        if val is not None:
            table.add_row(key, str(val))
    console.print(table)


@pdf_app.command("batch")
def cmd_batch(
    urls_file: Path = typer.Argument(..., help="Datei mit einer URL/Pfad pro Zeile. Kommentare mit # erlaubt."),
    output: Path = typer.Option(Path("pdf-extract.md"), "--out", "-o", help="Konkatenierte Markdown-Output-Datei."),
    skip_errors: bool = typer.Option(True, "--skip-errors/--strict", help="Fehler loggen und weitermachen oder abbrechen."),
) -> None:
    """Batch-Verarbeitung: liest Liste von URLs/Pfaden, schreibt einen Markdown-Report."""
    console = Console(stderr=True)
    if not urls_file.exists():
        typer.echo(f"Input-Datei nicht gefunden: {urls_file}", err=True)
        raise typer.Exit(1)

    lines = [
        ln.strip()
        for ln in urls_file.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    console.print(f"[bold]kit pdf batch[/bold] — {len(lines)} Eintrag(e) aus {urls_file}")

    infos: list[PDFInfo] = []
    for i, src in enumerate(lines, 1):
        console.print(f"[dim]({i}/{len(lines)}) {src}[/dim]")
        try:
            info = extract_text(src)
            infos.append(info)
            console.print(f"  [green]✓[/green] {info.num_pages} Seiten · {info.byte_size:,} Bytes")
        except Exception as e:  # noqa: BLE001 — Sammel-Logging
            if skip_errors:
                console.print(f"  [red]✗[/red] {type(e).__name__}: {e}")
                continue
            raise

    header = [
        f"# PDF Batch-Extract",
        "",
        f"Quelle: `{urls_file.name}` · Ausgeführt: {infos[0].fetched_at if infos else 'n/a'} · {len(infos)}/{len(lines)} erfolgreich",
        "",
        "---",
        "",
    ]
    body = [info.to_markdown() for info in infos]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(header) + "\n\n---\n\n".join(body) + "\n", encoding="utf-8")
    console.print(f"[bold green]→[/bold green] {output} ({output.stat().st_size:,} Bytes)")
