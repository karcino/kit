"""Core data structures and functions for kit docs.

No external dependencies beyond the Python standard library + PyYAML
(already a kit dependency).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml


FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)

# Normalize obsidian wiki-links like "[[Foo]]" or "[[1 - Projects/Foo]]"
# to their bare note name so parent: field can use any form.
WIKILINK_RE = re.compile(r"\[\[(?P<path>[^\]|]+?)(?:\|[^\]]*)?\]\]")


@dataclass
class DocNode:
    """A single document in the DAG.

    Paths are stored as absolute paths to make the DAG portable across
    subdirectories of a vault.
    """

    path: Path
    title: str
    type: str | None = None
    status: str | None = None
    parent_ref: str | None = None  # as written in frontmatter (may be wikilink)
    parent_path: Path | None = None  # resolved after build_dag
    body: str = ""
    frontmatter: dict = field(default_factory=dict)
    children: list[Path] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        """Hash of the document body (not frontmatter).

        Using body-only hash means updating the frontmatter itself
        (e.g., stamping `parent_synced`) does NOT invalidate children.
        Only substantive content changes do.
        """
        return content_hash(self.body)

    @property
    def stored_parent_hash(self) -> str | None:
        """The `parent_hash` field stored in this doc's frontmatter.

        If None, the doc has never been synced to its parent.
        If mismatching parent.content_hash, the doc is stale.
        """
        return self.frontmatter.get("parent_hash")

    @property
    def is_root(self) -> bool:
        return self.parent_ref is None


def content_hash(body: str) -> str:
    """Content-addressed hash of a document body. SHA-256 hex, truncated."""
    h = hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()
    return f"sha256:{h[:16]}"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into (frontmatter_dict, body).

    Returns ({}, text) if no frontmatter is present.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group("yaml")) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group("body")


def _resolve_parent_ref(ref: str, vault_root: Path, current_path: Path) -> Path | None:
    """Resolve a parent: reference to an absolute path.

    Supports:
    - Obsidian wikilink: `"[[Foo]]"` or `"[[1 - Projects/Foo]]"`
    - Relative markdown path: `"../Foo.md"`
    - Absolute path: `"/Users/.../Foo.md"`
    - Bare note name: `"Foo"` (searched across the vault)
    """
    if ref is None:
        return None

    # Strip wikilink wrapper
    m = WIKILINK_RE.match(ref)
    if m:
        ref = m.group("path").strip()

    ref = ref.strip()
    if not ref:
        return None

    # Absolute path?
    if ref.startswith("/"):
        p = Path(ref)
        return p if p.exists() else None

    # Relative path from current file?
    if ref.endswith(".md") or ref.endswith(".html"):
        candidate = (current_path.parent / ref).resolve()
        if candidate.exists():
            return candidate

    # Search the vault for a matching note
    # "1 - Projects/Foo" or just "Foo"
    target = ref if ref.endswith(".md") else f"{ref}.md"
    # Exact match first
    exact = list(vault_root.rglob(target))
    if exact:
        return exact[0].resolve()
    # Partial (last segment) match
    base = Path(target).name
    partial = list(vault_root.rglob(base))
    return partial[0].resolve() if partial else None


def load_doc(path: Path) -> DocNode | None:
    """Parse a single markdown file into a DocNode.

    Returns None if the file is unreadable or has no frontmatter at all.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    fm, body = parse_frontmatter(text)
    if not fm:
        # No frontmatter = not a managed doc. Skip.
        return None

    return DocNode(
        path=path.resolve(),
        title=fm.get("title") or path.stem,
        type=fm.get("type"),
        status=fm.get("status"),
        parent_ref=fm.get("parent"),
        body=body,
        frontmatter=fm,
    )


def build_dag(vault_root: Path) -> dict[Path, DocNode]:
    """Walk a vault, load every markdown doc with frontmatter, resolve parents.

    Returns a dict keyed by absolute path. Every returned DocNode has
    parent_path resolved (may be None for roots) and children populated.
    """
    vault_root = Path(vault_root).resolve()
    nodes: dict[Path, DocNode] = {}

    for md_path in sorted(vault_root.rglob("*.md")):
        # Skip templates and hidden directories
        if any(part.startswith(".") for part in md_path.parts):
            continue
        if "Templates" in md_path.parts:
            continue
        node = load_doc(md_path)
        if node is not None:
            nodes[node.path] = node

    # Resolve parents
    for node in nodes.values():
        if node.parent_ref in (None, "null"):
            continue
        parent_path = _resolve_parent_ref(node.parent_ref, vault_root, node.path)
        if parent_path and parent_path in nodes:
            node.parent_path = parent_path
            nodes[parent_path].children.append(node.path)

    return nodes


def find_stale(nodes: dict[Path, DocNode]) -> list[tuple[DocNode, DocNode, str]]:
    """Return (stale_child, parent, reason) tuples for every out-of-sync doc.

    A child is stale when:
    - It has a resolved parent AND
    - Its stored `parent_hash` is None (never synced) OR
    - Its stored `parent_hash` != parent.content_hash (parent changed since last sync)
    """
    stale: list[tuple[DocNode, DocNode, str]] = []
    for node in nodes.values():
        if node.parent_path is None:
            continue
        parent = nodes.get(node.parent_path)
        if parent is None:
            continue
        stored = node.stored_parent_hash
        current = parent.content_hash
        if stored is None:
            stale.append((node, parent, "never synced"))
        elif stored != current:
            stale.append((node, parent, f"parent changed ({stored[:22]}... → {current[:22]}...)"))
    return stale


def iter_tree(
    nodes: dict[Path, DocNode],
    root: DocNode,
    depth: int = 0,
) -> Iterable[tuple[int, DocNode]]:
    """Depth-first iteration over a subtree rooted at a given node."""
    yield depth, root
    for child_path in root.children:
        child = nodes.get(child_path)
        if child is not None:
            yield from iter_tree(nodes, child, depth + 1)
