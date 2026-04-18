# Kit YouTube — Transcript Fetcher

**Date:** 2026-04-18
**Status:** Shipped v1 (CLI + Python API + MCP tool). Integration with `docs` / `cal` deferred to cross-tool-integration-hooks.
**Author:** Paul Fiedler + Claude

---

## 1. Vision

Fetch the transcript of any YouTube video from the terminal or from an AI agent, without signing up for AgentPatch, without an API key, and without OAuth.

```bash
kit youtube transcript https://youtu.be/dQw4w9WgXcQ
kit youtube transcript dQw4w9WgXcQ --lang de,en
kit youtube transcript URL --json | jq -r '.segments[].text' | llm summarize
kit youtube transcript URL --plain | pbcopy
```

From an agent:

```text
kit_youtube_transcript(source="https://...", languages=["en"])
→ JSON with video_id, language, is_generated, segments, fetched_at
```

---

## 2. Architecture

Mirrors `route/`, `cal/`, `flights/`. Five-file pattern per `docs/guides/adding-a-tool.md`:

```
src/kit/youtube/
├── __init__.py        # re-exports
├── core.py            # TranscriptRequest, TranscriptSegment, TranscriptResult
├── client.py          # YouTubeTranscriptClient — wraps youtube-transcript-api
├── planner.py         # fetch_transcript() — one-liner orchestrator
├── commands.py        # `kit youtube transcript <URL>` Typer subcommand
└── mcp_tools.py       # kit_youtube_transcript MCP tool
```

No auth, no config field, no subscription. The external library is imported lazily so tests don't need it.

---

## 3. External dependency

`youtube-transcript-api` — third-party Python library that scrapes YouTube's public transcript endpoint (the same one the web player uses). No API key; a browser-like request from a residential IP is enough in practice.

- Pinned as `youtube-transcript-api>=1.0` in `pyproject.toml` (the 1.x API requires instantiating `YouTubeTranscriptApi()` and uses `.list()` rather than the 0.x class-level `list_transcripts`).
- Imported lazily inside `YouTubeTranscriptClient._load_fetcher` to keep `import kit` cheap and keep tests offline.
- Library exceptions are caught by **name** (`TranscriptsDisabled`, `NoTranscriptFound`, `VideoUnavailable`, `TooManyRequests`) and mapped to `YouTubeError`. This avoids a hard dependency on the library's exception hierarchy, which has shifted across versions.

---

## 4. URL parsing

`core.extract_video_id` accepts every common form:

| Input | Extracted ID |
|---|---|
| `dQw4w9WgXcQ` | `dQw4w9WgXcQ` |
| `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `dQw4w9WgXcQ` |
| `https://youtu.be/dQw4w9WgXcQ` | `dQw4w9WgXcQ` |
| `https://www.youtube.com/shorts/dQw4w9WgXcQ` | `dQw4w9WgXcQ` |
| `https://www.youtube.com/embed/dQw4w9WgXcQ` | `dQw4w9WgXcQ` |
| `https://m.youtube.com/watch?v=dQw4w9WgXcQ` | `dQw4w9WgXcQ` |
| `https://music.youtube.com/watch?v=dQw4w9WgXcQ` | `dQw4w9WgXcQ` |
| `https://vimeo.com/123` | `ValueError` |

Extra query parameters (`&t=42s`, `&feature=shared`) are ignored.

---

## 5. Data model

```python
TranscriptRequest   # source, languages=["en"], allow_generated=True; .video_id property
TranscriptSegment   # start, duration, text; .end property
TranscriptResult    # video_id, language, is_generated, segments,
                    # fetched_at, source="youtube-transcript-api";
                    # .total_duration, .plain_text properties
```

Language selection is **priority-ordered**: `languages=["de", "en"]` means "prefer German, fall back to English." Manual transcripts beat auto-generated unless `allow_generated=False` forces the caller to reject auto.

---

## 6. CLI surface

```
kit youtube transcript <SOURCE>
  --lang / -l en,de              language priority
  --no-generated                 reject auto-generated transcripts
  --json                         machine output
  --plain                        just the concatenated text (pipe-friendly)
```

Default output: Rich table with `[time] [text]` rows + "N segments · H:MM:SS total" footer.

Exit codes: 2 on `YouTubeError` or URL parse failure. Typer handles `--help`.

---

## 7. MCP surface

```
kit_youtube_transcript(
    source: str,
    languages: list[str] | None = None,
    allow_generated: bool = True,
) -> str   # JSON of TranscriptResult
```

Registered in `mcp_server.py` via `register_youtube_tools`. Returns `model_dump_json(indent=2)`.

---

## 8. Out of scope (v1)

- **Search for videos** — Kit doesn't do YouTube search. If you want that, add a separate `kit youtube search` subcommand backed by a different service (Invidious, YouTube Data API with an API key, etc.). Not today.
- **Batch fetch** — one video at a time. Agents can loop if they need more.
- **Translation** — we return the transcript in whatever language YouTube exposes. Use a separate tool (LLM, DeepL, etc.) for translation.
- **Audio / video download** — transcripts only.
- **Integration with `kit docs`** — the interesting scenario ("add this transcript to my knowledge DAG") is blocked on the cross-tool-integration-hooks decision at `docs/specs/2026-04-18-cross-tool-integration-hooks.md`. v1 returns data only.
- **Integration with `kit cal`** — same deferral ("attach this transcript summary to a calendar note").

---

## 9. Verified

- `pytest -m "not smoke"` — all tests pass (model + URL parsing + client fakes + planner + MCP tool wiring).
- Smoke test (`-m smoke`) hits the real library against `dQw4w9WgXcQ`. Run with an active network connection.

---

## 10. Why native instead of AgentPatch

The AgentPatch article (2026-01-06) proposes installing their CLI to access a YouTube transcript tool + their marketplace. That's a *buy* solution: faster to install, external dependency, their API key, their uptime.

Native is the *build* choice: fits Kit's three-interfaces-one-core pattern, no external service, no account, becomes part of the Kit portfolio story. For Kit's dominant intention (G2 — portfolio / Konstellation pitch), build beats buy because the story is *"my system, my surface,"* not *"reseller of someone else's tools."*

Full reasoning in the prior session's notes; decision captured here as rationale for future readers.
