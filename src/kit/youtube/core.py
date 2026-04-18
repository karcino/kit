"""Core data models for YouTube transcript fetching."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field, model_validator

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

_HOST_PATH_RULES: tuple[tuple[str, str], ...] = (
    ("youtu.be", "path"),
    ("www.youtube.com", "query_or_embed"),
    ("youtube.com", "query_or_embed"),
    ("m.youtube.com", "query_or_embed"),
    ("music.youtube.com", "query_or_embed"),
)


def extract_video_id(source: str) -> str:
    """Return the 11-char YouTube video ID from a URL or raw ID.

    Accepts:
      - https://www.youtube.com/watch?v=ID
      - https://youtu.be/ID
      - https://www.youtube.com/shorts/ID
      - https://www.youtube.com/embed/ID
      - https://music.youtube.com/watch?v=ID
      - Raw ID (11 chars, [A-Za-z0-9_-])

    Raises ValueError if no valid ID can be extracted.
    """
    source = source.strip()
    if not source:
        raise ValueError("Empty YouTube URL or video ID.")

    if _VIDEO_ID_RE.match(source):
        return source

    parsed = urlparse(source)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if host == "youtu.be":
        candidate = path.split("/", 1)[0]
        if _VIDEO_ID_RE.match(candidate):
            return candidate

    if host.endswith("youtube.com"):
        # /watch?v=ID
        query = parse_qs(parsed.query)
        if "v" in query and _VIDEO_ID_RE.match(query["v"][0]):
            return query["v"][0]
        # /shorts/ID or /embed/ID or /v/ID
        for prefix in ("shorts/", "embed/", "v/", "live/"):
            if path.startswith(prefix):
                candidate = path[len(prefix):].split("/", 1)[0]
                if _VIDEO_ID_RE.match(candidate):
                    return candidate

    raise ValueError(f"Could not extract a YouTube video ID from {source!r}.")


class TranscriptRequest(BaseModel):
    """A user-facing transcript request."""

    source: str = Field(description="YouTube URL or 11-char video ID")
    languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="Preferred language codes in priority order (e.g. ['en', 'de']). "
                    "First available wins; auto-generated transcripts are acceptable.",
    )
    allow_generated: bool = Field(
        default=True,
        description="Fall back to auto-generated transcripts if no manual one exists.",
    )

    @model_validator(mode="after")
    def _check_source(self) -> TranscriptRequest:
        # Validate extractability up front so callers fail fast.
        extract_video_id(self.source)
        return self

    @property
    def video_id(self) -> str:
        return extract_video_id(self.source)


class TranscriptSegment(BaseModel):
    """A single segment of a YouTube transcript."""

    start: float = Field(description="Start time in seconds from video start.")
    duration: float = Field(description="Segment duration in seconds.")
    text: str = Field(description="Transcript text for this segment.")

    @property
    def end(self) -> float:
        return self.start + self.duration


class TranscriptResult(BaseModel):
    """Result of a transcript fetch."""

    video_id: str
    language: str = Field(description="Actual language code returned.")
    is_generated: bool = Field(description="True if the transcript is auto-generated.")
    segments: list[TranscriptSegment]
    fetched_at: datetime
    source: Literal["youtube-transcript-api"] = "youtube-transcript-api"

    @property
    def total_duration(self) -> float:
        if not self.segments:
            return 0.0
        last = self.segments[-1]
        return last.end

    @property
    def plain_text(self) -> str:
        """All segment texts joined with single spaces."""
        return " ".join(s.text for s in self.segments).strip()
