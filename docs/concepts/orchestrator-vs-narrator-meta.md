# How this was made

> **Provenance report** for [`orchestrator-vs-narrator.html`](orchestrator-vs-narrator.html).
> Theme: [Kit-Spec-Stil](_design/kit-spec-stil.md).

This artifact is the first concrete **Narrator** output. The thing being described (a Narrator agent producing self-describing architecture docs) produced itself. This report is the transparency half of that bootstrap — it names the agent, the harness, the tools actually used, the tools that were available but not used, the data sources consulted, and the reasoning path.

Nothing here is inferred from training priors. Every claim grounds in a file or a system message that was visible to the agent at generation time.

---

## Contents

- [Model](#model)
- [Harness](#harness)
- [Output style](#output-style)
- [Skills invoked](#skills-invoked)
- [Tools used](#tools-used)
- [MCP servers available but not used](#mcp-servers-available-but-not-used)
- [Data sources consulted](#data-sources-consulted)
- [System-prompt composition](#system-prompt-composition)
- [Reasoning flow](#reasoning-flow)
- [Honest limits](#honest-limits)

---

## Model

| Field | Value |
|---|---|
| Model ID | `claude-opus-4-7[1m]` |
| Family | Claude Opus 4.7 |
| Context window | 1 000 000 tokens |
| Knowledge cutoff | January 2026 |
| Source | Claude Code system prompt, `Environment` block |

## Harness

- **Harness.** Claude Code CLI on macOS (Darwin 25.4.0, zsh).
- **Working directory.** A git worktree under
  `/Users/p.fiedler/Desktop/Code_Projects/kit/.claude/worktrees/frosty-rubin-bcfd7d`,
  branch `claude/frosty-rubin-bcfd7d`, forked from `main` at commit `233f154`.
- **Plan mode** was active during the preceding *design* session and produced the plan file at
  `~/.claude/plans/january-6-2026-how-adaptive-flame.md`, which drove this execution session.

## Output style

`learning` mode — interactive + explanatory. ★ Insight blocks surface in the conversation but stay out of committed files.

## Skills invoked

| Skill | When |
|---|---|
| `superpowers:using-superpowers` | auto-loaded at session start |
| `superpowers:brainstorming` | during the design session captured in the plan file |

Not re-invoked during execution — execution is not creative work.

## Tools used

Chronological, **execution session** (this session, which produced the files):

1. `Skill` — load `superpowers:using-superpowers`.
2. `ToolSearch` — load `TodoWrite` schema (deferred tool).
3. `Read` — plan file `~/.claude/plans/january-6-2026-how-adaptive-flame.md`.
4. `TodoWrite` — six-step execution checklist.
5. `Read` — `README.md`.
6. `Bash` — `ls docs/` to confirm `plans/`, `specs/` siblings.
7. `Glob` — enumerate `src/kit/**/*.py`.
8. `Bash` — `mkdir -p docs/concepts/` + worktree sanity check.
9. `Write` — `orchestrator-vs-narrator.html` (initial cut).
10. `Write` — `orchestrator-vs-narrator-meta.md` (initial cut).
11. `Bash` — `open` the HTML in Chrome for visual verification.
12. `Bash` — `osascript` + `say` for notification + TTS.
13. `ToolSearch` — load Notion MCP schemas after the harness exposed them.
14. `Write` — `_design/kit-spec-stil.md` (design library).
15. `Write` — this file (polished), `orchestrator-vs-narrator-meta.html` (rendered companion), and an updated `orchestrator-vs-narrator.html` with prose + theme link.
16. `mcp__notion-search` + `mcp__notion-create-pages` — Work Log row.

**Design session** (preceded execution, produced the plan file): `Read`, `Glob`, `ToolSearch` (for `TodoWrite`, `AskUserQuestion`, `ExitPlanMode`), `TodoWrite`, `AskUserQuestion`, `ExitPlanMode`, final `Write` of the plan.

## MCP servers available but not used

The harness exposed a wide deferred-tool surface. None of the following were loaded or called during design, and most were not called during execution either — they sat idle. Listed in full for honesty:

- `computer-use` — desktop control (screenshot / click / type).
- `Claude-in-Chrome` / `Control_Chrome` — browser DOM control.
- `Claude_Preview` — headless preview harness (note: preview panel rendering is a harness integration, not an MCP call).
- `Figma` suite (`use_figma`, `get_design_context`, etc.) — design system I/O.
- `Zotero` — literature management.
- `PDF Tools` — merge / split / fill.
- `iMessage` — read + send.
- `ccd_directory` — directory approvals.
- `plugin:context7:context7` — library documentation lookup.
- `mcp-registry` — connector discovery.
- `scheduled-tasks` — cron-style agent scheduling.
- Vercel bundle, Anthropic skill bundle, PR review toolkit, agent SDK verifiers.

The **Notion MCP** (`notion-search`, `notion-create-pages`, …) was **not available** during the initial execution turn. The harness exposed it in a later turn, at which point the Work Log row was created.

## Data sources consulted

- `~/Desktop/CLAUDE.md` — workspace conventions (completion-report pattern, notification + TTS discipline, Kit-Spec-Stil).
- `CLAUDE.md` at the worktree root — Kit architecture, testing conventions, MCP entry points.
- `README.md` — public surface, feature list, roadmap.
- `git status` + `git worktree list` — branch isolation confirmation.
- `Glob src/kit/**/*.py` — real module tree (`cal`, `route`, `utils`, `mcp_server`, `cli`, `config`, `errors`, `setup_cmd`).
- Memory index at `~/.claude/projects/-Users-p-fiedler-Desktop/memory/` — completion-workflow rules.
- The plan file — the primary driver; execution is a faithful read of it.

No external retrieval. No web fetch. No library doc lookup. The artifact was generated entirely from the agent's in-context view of the repo.

## System-prompt composition

Layers, in the order they arrived:

1. Claude Code base prompt — identity, tool discipline, safety protocols, git rules.
2. Environment injection — working directory, branch, git status snapshot, timestamp (2026-04-18).
3. Learning output-style preamble — ★ Insight convention, user-contribution invitation pattern.
4. `superpowers:using-superpowers` skill preamble — skill-first discipline.
5. MCP server instructions (`computer-use`, `context7`).
6. Deferred-tool notice — schemas on demand via `ToolSearch`.
7. Project `CLAUDE.md` blocks — workspace (`~/Desktop`) and project (Kit worktree) conventions.

## Reasoning flow

### Design session (preceded this)

1. Open frame: Kit's next direction.
2. Decomposed the ambition into three sequential sub-projects — agent-first redesign, natural-language orchestrator, hosted service.
3. **Service shape = C.** Universal front-door `/ask` endpoint, one engine, four clients (CLI, Python, MCP, HTTP).
4. **Engine = fast-LLM one-shot.** Add rules and loop tiers only on evidence. Chosen because the global intention prizes speed.
5. **Global intention = G2.** Portfolio / demo / Konstellation pitch. Rewards range and craft over reliability or personal fit.
6. **Pivot = Narrator first.** A *design-time* agent whose first output is G2 material on day one, so it pays off before the Orchestrator works.
7. The deliverable Paul asked for (this HTML + this report) is itself the first Narrator output — a bootstrap move.

### Execution session (this one)

1. Read plan, classified as mechanical execution (no re-brainstorm needed).
2. Confirmed `docs/` layout matches plan assumption.
3. Wrote HTML first (the visible artifact), then this meta (the transparency artifact), then visually verified.
4. Followed up with design library doc + prose section + rendered meta HTML after Paul asked for them in-flight.

## Honest limits

What this report **cannot** verify:

| Claim | Why not |
|---|---|
| Token counts | The agent does not see its own token budget or per-turn usage. |
| Wall-clock latency | No end-to-end timer; "fast" and "minutes" in the HTML are targets, not measurements. |
| API call counts | The agent does not observe provider-side request counts. |
| Completeness of the MCP non-use list | Niche deferred tools may exist that weren't noticed. Close-enough fidelity, not exhaustive. |
| Transcript fidelity of the design session | The plan file is a summary. Micro-decisions elided there are inherited as elided here. |

---

Generated 2026-04-18 · Kit Narrator v0 · `claude-opus-4-7[1m]` · theme: [Kit-Spec-Stil](_design/kit-spec-stil.md)
