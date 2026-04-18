"""Tests for kit docs.core."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from kit.docs.core import (
    DocNode,
    build_dag,
    content_hash,
    find_stale,
    parse_frontmatter,
)


def test_content_hash_deterministic() -> None:
    h1 = content_hash("hello world")
    h2 = content_hash("hello world")
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_content_hash_differs_on_change() -> None:
    assert content_hash("foo") != content_hash("bar")


def test_parse_frontmatter_present() -> None:
    text = dedent("""\
        ---
        title: Test
        parent: "[[Parent]]"
        ---
        Body content
    """)
    fm, body = parse_frontmatter(text)
    assert fm["title"] == "Test"
    assert fm["parent"] == "[[Parent]]"
    assert "Body content" in body


def test_parse_frontmatter_missing() -> None:
    fm, body = parse_frontmatter("no frontmatter here")
    assert fm == {}
    assert body == "no frontmatter here"


def test_build_dag_minimal(tmp_path: Path) -> None:
    (tmp_path / "parent.md").write_text(dedent("""\
        ---
        title: Parent
        ---
        I am the root.
    """))
    (tmp_path / "child.md").write_text(dedent("""\
        ---
        title: Child
        parent: parent
        ---
        I derive from Parent.
    """))
    nodes = build_dag(tmp_path)
    assert len(nodes) == 2
    parent = next(n for n in nodes.values() if n.title == "Parent")
    child = next(n for n in nodes.values() if n.title == "Child")
    assert child.parent_path == parent.path
    assert child.path in parent.children


def test_build_dag_skips_templates(tmp_path: Path) -> None:
    (tmp_path / "Templates").mkdir()
    (tmp_path / "Templates" / "notiz.md").write_text(dedent("""\
        ---
        title: Template
        ---
        template body
    """))
    (tmp_path / "real.md").write_text(dedent("""\
        ---
        title: Real
        ---
        real body
    """))
    nodes = build_dag(tmp_path)
    assert len(nodes) == 1
    assert list(nodes.values())[0].title == "Real"


def test_find_stale_never_synced(tmp_path: Path) -> None:
    (tmp_path / "parent.md").write_text(dedent("""\
        ---
        title: P
        ---
        body
    """))
    (tmp_path / "child.md").write_text(dedent("""\
        ---
        title: C
        parent: parent
        ---
        body
    """))
    nodes = build_dag(tmp_path)
    stale = find_stale(nodes)
    assert len(stale) == 1
    child, parent, reason = stale[0]
    assert child.title == "C"
    assert parent.title == "P"
    assert "never synced" in reason


def test_find_stale_in_sync(tmp_path: Path) -> None:
    parent_body = "body\n"
    parent_hash = content_hash(parent_body)
    (tmp_path / "parent.md").write_text(dedent(f"""\
        ---
        title: P
        ---
        {parent_body}""").rstrip() + "\n")
    (tmp_path / "child.md").write_text(dedent(f"""\
        ---
        title: C
        parent: parent
        parent_hash: {parent_hash}
        ---
        child body
    """))
    nodes = build_dag(tmp_path)
    stale = find_stale(nodes)
    assert stale == []


def test_build_dag_on_real_vault() -> None:
    """Smoke test: make sure the DAG builder handles the actual Paul vault."""
    vault = Path("/Users/p.fiedler/Desktop/Vault")
    if not vault.exists():
        pytest.skip("Real vault not available")
    nodes = build_dag(vault)
    # Should find at least the project notes we just created
    titles = {n.title for n in nodes.values()}
    assert "Kulturradar" in titles
    assert "Kuratierte Galerie (working title)" in titles
    assert "Konstellation Framework" in titles
