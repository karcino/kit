# Kit-Spec-Stil — design theme

```
[composition: form=principles+tokens+reference · stages=headline+tagline+scan+reference · level=concept+artifact · link=within-doc · meta=off]
```

**Monospace, sachlich, four tokens, two layouts.**
Design system for Kit's concept documents and provenance reports.
All files in [`docs/concepts/`](..) follow this theme.
Composition rules (depth / form / linking) live in the sibling
[`narrator-presentation-spec.md`](narrator-presentation-spec.md).

> **Scope.** Currently lives inside the Kit repo. If adopted outside Kit
> (other Paul-workspace projects), promote this file to
> `~/Desktop/Planung/_design/kit-spec-stil.md` and reference it via
> absolute `file://` from consuming docs.

---

## Principles

1. **Monospace everywhere.** No serif. Reading text and tabular data share one typeface.
2. **Sachlich.** Text-only punctuation (`·`, `→`, `↗`, `†`). No decorative emoji. Functional markers only (`✓`, `→`).
3. **High contrast.** `#111` on `#f4f4f2`. Dark mode is a later variant, not a default.
4. **Structure visible.** Rules between blocks, labels above values, one font weight per section.
5. **No info overload.** An artifact should fit its idea. If a page needs a second screen, the prose earns it.

## Tokens

### Color

| Token      | Value     | Use                                   |
|------------|-----------|---------------------------------------|
| `--bg`     | `#f4f4f2` | page background                       |
| `--fg`     | `#111`    | body text, titles, rules              |
| `--muted`  | `#555`    | labels, metadata, footnotes           |
| `--rule`   | `#111`    | outer block rules (1px solid)         |
| _(inner)_  | `#bbb`    | inner separators (1px dashed)         |

### Type

| Role           | Size | Weight | Tracking    | Line-height |
|----------------|------|--------|-------------|-------------|
| Title          | 18px | 700    | `-0.01em`   | 1.2         |
| Section head   | 15px | 700    | `0.02em`    | 1.3         |
| Body tabular   | 13px | 400    | normal      | 1.45        |
| Body prose     | 14px | 400    | normal      | 1.65        |
| Label          | 12px | 400    | `0.06–0.08em`, `UPPERCASE` | 1.3         |

Font stack: `ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace`.

### Spacing + layout

- Page padding: `32px 40px`.
- Two-column comparison grid: `grid-template-columns: 1fr 1px 1fr; gap: 28px;` with a `.rule` spacer.
- Prose: single column, `max-width: 72ch`, left-aligned, never justified.
- Row separator inside a section: `1px dashed #bbb`.
- Block separator: `1px solid var(--rule)`.
- No drop shadows, no gradients, no `border-radius > 0`.

### Links

- Always underlined.
- `text-underline-offset: 3px`.
- Hover: invert (`background: var(--fg); color: var(--bg);`).
- External links end with a small `↗` (glyph, not icon font).
- In-page / cross-doc links end with `→`.

## Layouts

### Two-column comparison
Used for side-by-side concepts (Orchestrator vs Narrator). Equal columns, a single 1px vertical rule between. Each row is `[label | value]` with a dashed top border.

### Long-form prose
Single column constrained to `72ch`. Inline glossary terms are links with `↗` suffix to Wikipedia or authoritative specs. The prose section lives below the comparison grid, never replaces it.

### Software docs
For meta-reports and provenance docs. Still monospace, still these tokens, but with:
- `max-width: 78ch`
- Heading scale `h1 20px / h2 16px / h3 14px`
- Table of contents at top
- Horizontal rule between top-level sections

## Reference implementations

| File | Pattern |
|---|---|
| [`../orchestrator-vs-narrator.html`](../orchestrator-vs-narrator.html) | comparison + prose |
| [`../orchestrator-vs-narrator-meta.html`](../orchestrator-vs-narrator-meta.html) | software docs |
| [`../orchestrator-vs-narrator-meta.md`](../orchestrator-vs-narrator-meta.md) | GitHub markdown render of same content |

## Rules (don'ts)

- Don't introduce a second font family.
- Don't add colors beyond the four above without extending this file first.
- Don't use icon fonts. If an icon is required, Unicode or inline SVG only.
- Don't center body text.
- Don't animate.
- Don't use shadow, blur, or gradient to imply hierarchy. Use rules and weight.

---

Last updated: 2026-04-18 · sibling: [narrator-presentation-spec](narrator-presentation-spec.md) · initial cut, co-authored by the Narrator with Paul.
