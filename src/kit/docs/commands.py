"""Typer CLI commands for kit docs.

Commands:
- kit docs tree [VAULT]      — print the DAG from every root
- kit docs check [VAULT]     — list stale descendants
- kit docs graph [VAULT]     — emit Mermaid graph source
- kit docs sync DOC          — stamp current parent_hash in a child's frontmatter
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from kit.docs.core import DocNode, build_dag, find_stale, iter_tree


DEFAULT_VAULT = Path("~/Desktop/Vault").expanduser()

docs_app = typer.Typer(
    name="docs",
    help="Hierarchical document DAG with change propagation.",
    no_args_is_help=True,
)


def _load(vault: Path) -> dict[Path, DocNode]:
    if not vault.exists():
        typer.echo(f"Vault not found: {vault}", err=True)
        raise typer.Exit(1)
    return build_dag(vault)


@docs_app.command("tree")
def cmd_tree(
    vault: Path = typer.Argument(DEFAULT_VAULT, help="Vault root"),
) -> None:
    """Print the document DAG as a tree, grouped by root."""
    console = Console()
    nodes = _load(vault)

    roots = [n for n in nodes.values() if n.is_root or n.parent_path is None]
    if not roots:
        console.print("[yellow]No root documents found in vault[/]")
        return

    for root in sorted(roots, key=lambda n: n.title):
        tree = Tree(f"[bold]{root.title}[/] [dim]({root.type or 'doc'})[/]")
        _build_rich_tree(nodes, root, tree)
        console.print(tree)
        console.print()

    console.print(
        f"[dim]{len(nodes)} docs total · "
        f"{len(roots)} roots · "
        f"{sum(len(n.children) for n in nodes.values())} edges[/]"
    )


def _build_rich_tree(nodes: dict[Path, DocNode], node: DocNode, tree: Tree) -> None:
    for child_path in sorted(node.children, key=lambda p: nodes[p].title if p in nodes else str(p)):
        child = nodes.get(child_path)
        if child is None:
            continue
        label = f"{child.title} [dim]({child.status or child.type or '—'})[/]"
        subtree = tree.add(label)
        _build_rich_tree(nodes, child, subtree)


@docs_app.command("check")
def cmd_check(
    vault: Path = typer.Argument(DEFAULT_VAULT, help="Vault root"),
) -> None:
    """List documents whose parent has changed since last sync."""
    console = Console()
    nodes = _load(vault)
    stale = find_stale(nodes)

    if not stale:
        console.print("[green]✓[/] All tracked documents are in sync with their parents.")
        console.print(f"[dim]{len(nodes)} docs checked[/]")
        return

    table = Table(title=f"Stale documents ({len(stale)})", show_lines=False)
    table.add_column("Child", style="bold")
    table.add_column("Parent", style="cyan")
    table.add_column("Reason", style="yellow")
    for child, parent, reason in stale:
        table.add_row(child.title, parent.title, reason)
    console.print(table)

    console.print()
    console.print("[dim]Run [bold]kit docs sync <child>[/] after reviewing each stale child.[/]")
    raise typer.Exit(1)


@docs_app.command("graph")
def cmd_graph(
    vault: Path = typer.Argument(DEFAULT_VAULT, help="Vault root"),
    format: str = typer.Option("mermaid", "--format", "-f", help="Output format: mermaid"),
) -> None:
    """Emit a Mermaid graph of the document DAG."""
    nodes = _load(vault)
    if format != "mermaid":
        typer.echo(f"Format {format!r} not yet supported — use 'mermaid'", err=True)
        raise typer.Exit(1)

    typer.echo("graph TD")
    counter = 0
    id_for_path: dict[Path, str] = {}
    for path, node in nodes.items():
        counter += 1
        id_for_path[path] = f"n{counter}"
        label = node.title.replace('"', "'")
        shape = f'["{label}"]'
        if node.type == "meta":
            shape = f'(("{label}"))'
        elif node.type == "area":
            shape = f'["{label}"]'
        typer.echo(f"  {id_for_path[path]}{shape}")

    for path, node in nodes.items():
        for child_path in node.children:
            if child_path in id_for_path:
                typer.echo(f"  {id_for_path[path]} --> {id_for_path[child_path]}")


@docs_app.command("sync")
def cmd_sync(
    doc: Path = typer.Argument(..., help="Path to the child doc to sync"),
    vault: Path = typer.Option(DEFAULT_VAULT, "--vault", help="Vault root"),
) -> None:
    """Stamp the current parent content_hash into a child doc's frontmatter.

    Call this AFTER reviewing a stale child and deciding it no longer needs
    further edits relative to the parent's new content.
    """
    console = Console()
    nodes = _load(vault)
    target = doc.resolve()

    node = nodes.get(target)
    if node is None:
        console.print(f"[red]Not a tracked doc:[/] {doc}")
        raise typer.Exit(1)
    if node.parent_path is None:
        console.print(f"[yellow]Root doc (no parent to sync):[/] {node.title}")
        raise typer.Exit(1)

    parent = nodes[node.parent_path]
    new_hash = parent.content_hash
    console.print(f"Stamping [bold]{node.title}[/] with parent hash [cyan]{new_hash}[/]")
    console.print("[dim](write-back not yet implemented — manual frontmatter edit required)[/]")
    # Write-back is deliberately left as a manual step in the MVP so that
    # no-one can accidentally rewrite files without reviewing the diff first.
    # Phase 2 of kit docs will add guarded write-back with `--yes`.
