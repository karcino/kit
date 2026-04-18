# How this was made — provenance for `orchestrator-vs-narrator.html`

Companion to [`orchestrator-vs-narrator.html`](./orchestrator-vs-narrator.html).

This document exists because agentic artifacts should ship with their own provenance. If you read the HTML, you see the conclusions. If you read this, you see the circumstances that produced them: model, harness, skills, tool calls, data sources, system-prompt composition, reasoning chain — and what I cannot honestly claim to know. It is the first output in the shape the Kit **Narrator** agent is designed to produce.

---

## 1. Model & harness

| | |
|---|---|
| Model | `claude-opus-4-7[1m]` — Claude Opus 4.7, 1M context window |
| Knowledge cutoff | January 2026 |
| Harness | Claude Code CLI (Anthropic's official CLI for Claude) |
| Platform | macOS (Darwin 25.4.0), shell: zsh |
| Working directory | `/Users/p.fiedler/Desktop/Code_Projects/kit` |
| Mode during design | **Plan mode** (read-only except the plan file) — exited before any file was written |
| Output style | `learning` (interactive + educational, `★ Insight` blocks enabled) |
| Session date | 2026-04-18 (per environment injection) |

At the moment the `/context` slash command ran, total context usage was **145.3k / 1M tokens (15%)**. Breakdown:

| Layer | Tokens | % |
|---|---:|---:|
| System prompt | 8.7k | 0.9% |
| System tools (loaded) | 18.6k | 1.9% |
| System tools (deferred, name-only) | 14.4k | 1.4% |
| MCP tools (loaded) | 1.3k | 0.1% |
| MCP tools (deferred, name-only) | 76.6k | 7.7% |
| Custom agents | 4.9k | 0.5% |
| Memory files | 2.9k | 0.3% |
| Skills | 5.7k | 0.6% |
| Messages (conversation) | 108.3k | 10.8% |
| Free space | 816.6k | 81.7% |
| Auto-compact buffer reserved | 33k | 3.3% |

---

## 2. Skills invoked

Two skills entered the conversation explicitly:

- **`superpowers:using-superpowers`** — auto-loaded at session start via a system-reminder inject. Establishes the rule that relevant skills must be invoked before any substantive response.
- **`superpowers:brainstorming`** — invoked via the `Skill` tool at the start of this session. Governed: one-question-at-a-time clarification, the decomposition-before-design scope check, the hard gate against implementation before a written and approved design, and the terminal state of transitioning to `writing-plans`.

Many other skills were *available but not invoked* — see §6.

---

## 3. Tool calls (chronological)

In order of first use, the tools that produced this session's state:

1. `Skill` → `superpowers:using-superpowers` (activated via system inject)
2. `Skill` → `superpowers:brainstorming` (activated explicitly)
3. `ToolSearch` — loaded deferred schemas for `TodoWrite`, `AskUserQuestion`, `ExitPlanMode`
4. `Glob` — `src/kit/**/*.py` and `src/kit/docs/**/*`
5. `Read` — `/Users/p.fiedler/Desktop/Code_Projects/kit/README.md`
6. `TodoWrite` — initial brainstorming checklist (created, later updated)
7. `AskUserQuestion` — seven multiple-choice clarifications, one per topic (service shape, sub-project ordering, orchestrator ambition, primary framing, engine style, dominant goal, narrative priority, composition, next step)
8. `Write` — plan file at `/Users/p.fiedler/.claude/plans/january-6-2026-how-adaptive-flame.md`
9. `mcp__ccd_session__spawn_task` — offered a one-click fork chip for the artifact build
10. `TodoWrite` — two progress updates across the session
11. *This turn:* `Bash` (`mkdir -p docs/concepts && ls`), `Write` (HTML), `Write` (this meta), `Bash` (open in Chrome + notification)

---

## 4. Data sources consulted

What the model *actually read*:

| Source | How reached |
|---|---|
| `/Users/p.fiedler/Desktop/CLAUDE.md` | Auto-loaded at session start (workspace-level instructions) |
| `/Users/p.fiedler/Desktop/Code_Projects/kit/CLAUDE.md` | Auto-loaded at session start (project-level instructions) |
| `/Users/p.fiedler/Desktop/Code_Projects/kit/README.md` | `Read` tool |
| `src/kit/**/*.py` file list | `Glob` tool |
| `src/kit/docs/**/*` file list | `Glob` tool |
| Git status snapshot | Initial environment injection |
| Live `/context` output | User-invoked slash command during this final turn |
| The user's typed messages | The conversation itself |

**Not consulted:** the Master Index Notion database, the Obsidian vault, any git history, the contents of `src/kit/docs/core.py` or `commands.py` (only their paths were globbed), any remote URLs, any of the available MCP servers in §6. The design conversation was conducted entirely against the files above plus the conversation.

---

## 5. System-prompt composition

Layers present in the model's system prompt during this session (described, not quoted):

- Claude Code base system prompt — identity, safety, tool etiquette, commit/PR conventions.
- Environment injection — working directory, git branch (`main`), git status, platform, date (2026-04-18), model ID.
- **Plan-mode injection** (active during design) — restricted edits to the plan file, defined a five-phase workflow, required `ExitPlanMode` as the terminal action.
- **Learning output-style instructions** — `★ Insight` blocks, educational framing, user-contribution prompts for meaningful design decisions.
- `superpowers:using-superpowers` skill preamble — the "invoke skills before any response" rule.
- MCP server-specific user-facing instructions — explicitly provided by `computer-use` and `plugin_context7_context7`.
- Deferred-tool manifest — tool names listed; schemas fetched on demand via `ToolSearch`.
- Available-skills list.
- `claudeMd` section containing both auto-loaded CLAUDE.md files verbatim.
- Session environment: `userEmail` = `p.fiedler@posteo.de`, `currentDate` = `2026-04-18`.

---

## 6. MCP surroundings — available, none used

The following MCP servers were connected at session start. **None were invoked** during the design phase. One was invoked during this final build turn: `mcp__ccd_session__spawn_task` (to offer the fork chip).

- `computer-use` — macOS desktop control (click, type, screenshot, app launch)
- `Claude_in_Chrome` — DOM-aware browser control (navigation, forms, page reads)
- `Claude_Preview` — dev-server preview tools
- `Control_Chrome` — lightweight browser tab control
- `Control_your_Mac` — AppleScript execution
- Notion (UUID-named server) — workspace, database, page, comment, search
- Figma (UUID-named server) — design context, variables, code connect
- Zotero — bibliographic search, annotation, metadata
- PDF Tools — read, fill, merge, split, extract
- `Read_and_Send_iMessages`
- `scheduled-tasks`
- `mcp-registry` — discovery of additional connectors
- `plugin_context7_context7` — library documentation lookup
- `ccd_directory`, `ccd_session` — Claude Code session tooling

The **listing itself** is a description of the agent's surroundings — reachable capabilities that were deliberately not used. For a brainstorming artifact, that absence is appropriate. For a task that claimed to query Notion or inspect a PDF, the absence of the corresponding tool calls would be a red flag.

---

## 7. Reasoning flow — the decision chain

The conversation followed a depth-first refinement pattern governed by `superpowers:brainstorming`. Each question resolved one dimension before proceeding to the next:

1. **Scope / sub-project split.** The ambiguous brief ("brainstorm an AI-native Kit tool service") decomposed into three sub-projects: (1) agent-first tool redesign, (2) natural-language orchestrator, (3) hosted service. User confirmed the orchestrator as the conceptually rich piece, to be brainstormed first but "thought together" with the others.
2. **Service shape → C (universal front-door).** The orchestrator resolved architecturally to a single `/ask` endpoint with CLI, MCP, Python, and HTTP as symmetric clients. Local-first, hosted later.
3. **Engine personality → fast-LLM one-shot, with hybrid trajectory.** A comparison of rules-dispatch, single-LLM, iterative-loop, and hybrid-cascade engines against a stated latency priority. Recommendation: ship fast-LLM one-shot; climb the hybrid ladder on evidence.
4. **Global intention → G2 (portfolio / demo / Konstellation pitch).** Framed as the pressure that breaks trade-offs. Chosen over G1 (personal productivity) and G3 (commercial product).
5. **Narrative priority.** Ranked (not forced): AI-native architecture (thesis) › personal AI operator (differentiator) › solo→platform (arc) › speed+composition (receipts).
6. **Pivot: Narrator first.** User proposed a second agent that "illustrates and documents possible developments and concepts." Named it the **Narrator** (design-time), distinguished from the **Orchestrator** (runtime). For a G2-dominant intent, Narrator-first is the stronger opening move: its output is portfolio material on day 1, before the Orchestrator even works. The artifact the user then requested — this HTML plus a linked provenance meta — was itself a first Narrator output. Bootstrap move: the thing being designed produced its own first output.

---

## 8. What I cannot honestly verify

Explicit uncertainty. An artifact that pretends to know everything is worse than one that doesn't:

- **Wall-clock latency** of any LLM call in this session. Not measured.
- **Per-request token counts** for individual turns. Only the running total (145.3k) at the moment `/context` ran is known.
- **Prompt-cache hit rate.** Not observable from inside the model.
- **Which exact API endpoints** the harness calls. Inferred, not seen.
- **Whether auto-compaction has fired** during this session. A 33k buffer is reserved; events are not reported in-conversation.
- **Whether the user clicked the `spawn_task` chip** offered earlier this session. Unobservable from inside the conversation.
- **The current disk contents of either CLAUDE.md** file. The system-prompt injection is trusted; the files on disk were not re-read at the time of writing.
- **The user's exact intent distribution** for Kit in practice. Used as a framing assumption, not a measured fact.

---

## 9. Lineage

**Upstream** — the plan file that shaped this artifact:
`/Users/p.fiedler/.claude/plans/january-6-2026-how-adaptive-flame.md`

**Downstream** — three specs that should follow, each through its own brainstorm → design → implementation cycle:

1. **Full Narrator spec** — retrieval sources, output templates, invocation surfaces (`kit reflect`, `kit narrate`, ambient documentation).
2. **Orchestrator runtime spec** — engine, tool schemas, streaming, state, CLI/MCP/HTTP surfaces on one service.
3. **Hosted service spec** — `kit serve`, auth, deploy trajectory (Hetzner → domain), observability.

---

*This document is the provenance sibling of its subject. If you trust this, you know what to trust in the HTML.*
