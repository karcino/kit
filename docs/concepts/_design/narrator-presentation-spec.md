# Narrator presentation spec

Composition rules for documents produced by the Narrator (the design-time
agent in [Kit's Orchestrator-vs-Narrator](../orchestrator-vs-narrator.html)
architecture). Visual theme lives in [`kit-spec-stil.md`](kit-spec-stil.md);
this file is about *organisation* — depth, shape, linking, motion, defaults.

**Invocation.** When Paul is not satisfied with a document's design or
organisation, reference this file by path:

```
/apply docs/concepts/_design/narrator-presentation-spec.md
```

The spec tells the Narrator how to re-cut the artifact.

---

## 1 · Default-inference principle

Before any flag, the Narrator infers defaults from three signals:

| Signal | Question | Where it comes from |
|---|---|---|
| **Purpose** | portfolio-facing · internal note · onboarding · operational ref | the plan file, the request phrasing, or the surrounding project |
| **Audience** | Paul alone · an agent reading this · a third party · mixed | explicit ("für X"), or inferred from destination (Notion page vs Kit repo vs pitch folder) |
| **Request shape** | compare · explain · document · summarize · plan | grammatical mood of the request + keywords |

The principle:

> **Guess visibly, never silently.** The Narrator picks the most
> portfolio-ready composition that fits the three signals and states its
> composition choices in a one-line `[composition: ...]` strip at the top of
> the artifact. Paul overrides with a flag; Narrator never defends the guess.

If signals conflict, the Narrator asks *one* clarifying question — and only
if the wrong guess would waste more than ~5 minutes of iteration.

---

## 2 · Form ladder

Shapes available, in the order of increasing surface:

| Form | When it fits | Example |
|---|---|---|
| `scan` | a single fact or a 2–5 item enumeration | a stat, a list of files, a command line |
| `list` | a flat enumeration of homogeneous items | glossary, checklist, API table |
| `table` | two dimensions, both finite | token grid, honest-limits matrix |
| `compare` | exactly two (or three) entities with matching axes | Orchestrator vs Narrator |
| `timeline` | ordered steps, decisions, or history | plan stages, commit sequence |
| `prose` | continuous reasoning or narrative | long-form explainer |
| `provenance` | reflexive report about the artifact itself | the meta-report |

Forms **combine** with `+`. The main artifact from 2026-04-18 is
`compare + prose + glossary`, with a linked `provenance` sibling.

## 3 · Summary-stage ladder

Stages sit on an axis from low-bandwidth (fast scan) to high-bandwidth (full
context). A single document can stack multiple stages top-to-bottom:

| Stage | Bandwidth | Typical height | Purpose |
|---|---|---|---|
| **Headline** | 1 glance | 1 line | what is this |
| **Tagline** | 2 sec | 1 sentence | why it matters |
| **Scan** | 5 sec | a table / grid | shape of the thing |
| **Prose** | 30–90 sec | 3–6 paragraphs | the reasoning |
| **Reference** | as needed | glossary, link index | the vocabulary |
| **Provenance** | for skeptics | a full meta-report | how it was made |

A well-composed artifact exposes the right *subset* of these stages for its
audience. Never all six at once unless the artifact is a one-off deliverable
with mixed audience (like the Orchestrator-vs-Narrator page, which hits all
six on purpose).

## 4 · Levels of abstraction

Per artifact, be explicit about which level(s) you are operating at:

1. **Concept** — agent, service, intent, latency (vocabulary)
2. **Named artifact** — `Orchestrator`, `kit_route`, `POST /ask` (proper nouns)
3. **Implementation** — source files, tool names (`Read`, `Glob`), data paths
4. **Provenance** — model, harness, tool calls, system-prompt layers

Do not mix two levels in the same paragraph without a visual cue (a rule, a
label, a monospace inline span). Mixing is the most common failure mode.

## 5 · Linking patterns

| Pattern | Glyph | Use |
|---|---|---|
| **External reference** | `↗` | Wikipedia, specs, third-party docs |
| **Within-doc anchor** | `→` (context) or none (row click) | label/row → passage in prose |
| **Sibling doc** | `→` | theme, meta, source-md |
| **Provenance** | "How this was made" link, always top-right | every Narrator artifact carries one |
| **Source exposure** | `view markdown source ↗` | rendered HTML links to its .md twin |

**Highlight-on-jump.** When an in-doc anchor is followed, the target span
flashes per the [motion grammar](#6-motion-grammar). Never use blinking;
never use permanent bright highlight.

**No orphan anchors.** Every anchor ID used in a link must exist in the
prose, and every labelled concept in a grid must have a prose passage to
land on.

## 6 · Motion grammar

Three-phase journey for attention cues (highlight on jump, newly revealed
blocks, etc.):

| Phase | Duration | Behaviour |
|---|---|---|
| **Arrival** | 0 ms (instant) | full saturation, no transition-in |
| **Hold** | 1400 ms | color sustained — read-time window |
| **Release** | 2800 ms | `cubic-bezier(0.2, 0, 0, 1)` fade to transparent |

Total ≈ 4.2 s. Reduced-motion: instant on, 600 ms off, no smooth scroll.

Other motion defaults:

| Use | Duration | Easing |
|---|---|---|
| Hover affordance | 120 ms | `ease-out` |
| Tab / view switch | 220 ms | standard ease |
| Modal or new section entry | 320 ms | emphasized decelerate |

Never animate layout. Never animate longer than 500 ms for UI affordances;
only attention-journey cues earn the 4.2 s envelope.

## 7 · Feature flags

Terminal-style grammar. Defaults in **bold**.

| Flag | Values | Default | Effect |
|---|---|---|---|
| `--form` | `scan`, `list`, `table`, `compare`, `timeline`, `prose`, `provenance`, combinable with `+` | **auto** | top-level shape |
| `--stages` | any subset of `headline,tagline,scan,prose,reference,provenance`, `+`-joined | **auto** | which stages appear |
| `--level` | `concept`, `artifact`, `implementation`, `provenance`, `+`-joined | **concept+artifact** | abstraction levels |
| `--link` | `none`, `row`, `word`, `both` | **both** when `compare+prose` | clickable surfaces |
| `--glossary` | `off`, `inline`, `footer`, `both` | **footer** if ≥3 domain terms | term definitions |
| `--motion` | `off`, `reduced`, `standard`, `designed` | **designed** | animation envelope |
| `--theme` | theme id | **`kit-spec-stil`** | visual theme |
| `--source` | `hide`, `expose`, `dual` | **dual** (.md + .html both) | source accessibility |
| `--meta` | `off`, `linked`, `embedded` | **linked** when artifact is portfolio-facing | provenance report |
| `--anchors` | `on`, `off` | **on** when prose present | deep-linkable spans |
| `--width` | `tight` 60ch, `standard` 72ch, `wide` 80ch | **standard** | reading width |
| `--contrast` | `soft`, `standard`, `high` | **standard** | palette intensity |
| `--language` | `de`, `en`, `mixed` | **mixed** (Paul's working mode) | primary language |
| `--density` | `airy`, `standard`, `tight` | **standard** | padding/line-height |

**Order of override.** CLI flags (explicit) > request signals (inferred) >
spec defaults (this file) > theme defaults (kit-spec-stil).

**Composition strip.** The Narrator prints the active composition at the
top of the artifact as a single monospace line, e.g.:

```
[composition: form=compare+prose+glossary · stages=scan→provenance · link=both · meta=linked]
```

Paul reads that strip, decides whether to override, and invokes the spec
with the flags that need to change.

## 8 · Invocation examples

```
/apply narrator-presentation-spec --form=prose --stages=tagline+prose+reference
# → kill the grid, keep the long-form explainer + glossary

/apply narrator-presentation-spec --meta=embedded --source=hide
# → fold the meta-report into the main document; drop the .md twin

/apply narrator-presentation-spec --motion=reduced --contrast=high
# → accessibility-first rebuild

/apply narrator-presentation-spec --form=timeline --level=implementation
# → re-shape the artifact as a step-by-step flow at file/function granularity
```

An unflagged invocation (`/apply narrator-presentation-spec`) tells the
Narrator: *re-read your defaults, recompose the artifact, print the new
composition strip, ship.*

---

## Rules (don'ts)

- Don't stack more than four stages without a visible rule between them.
- Don't combine `scan` and `prose` without at least one navigable link
  between them — an unlinked comparison grid above prose is dead weight.
- Don't hide the composition strip. Transparency > polish.
- Don't re-compose silently in response to vague feedback. If Paul says
  "this feels off," ask *which flag*.
- Don't nest feature-flag grammars (no flags-of-flags). One flat namespace.

---

Last updated: 2026-04-18 · theme: [Kit-Spec-Stil](kit-spec-stil.md) ·
sibling: [how-this-was-made meta](../orchestrator-vs-narrator-meta.md)
