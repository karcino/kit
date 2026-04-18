"""kit docs — hierarchical document DAG with change propagation.

Reads YAML frontmatter from markdown files, builds a parent/child graph,
detects when a parent has changed content and flags stale descendants.

First real implementation of the Ubu-Panel "connection map" vision,
scoped down to: edges between docs, change propagation, mermaid output.

See ~/.claude/plans/piped-mapping-lagoon.md — Layer 2.
"""

from kit.docs.core import DocNode, build_dag, parse_frontmatter, content_hash, find_stale

__all__ = ["DocNode", "build_dag", "parse_frontmatter", "content_hash", "find_stale"]
