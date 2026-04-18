"""Thin wrapper over youtube-transcript-api.

The external library is imported lazily inside the client class so that
tests can patch it without pulling the real dependency at module import
time. Map all library-specific exceptions onto `YouTubeError` so CLI /
MCP consumers see a consistent error type.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from kit.errors import YouTubeError
from kit.youtube.core import (
    TranscriptRequest,
    TranscriptResult,
    TranscriptSegment,
    extract_video_id,
)


class _TranscriptFetcher(Protocol):
    """Minimal contract we need from youtube-transcript-api.

    Defined as a Protocol so tests can inject a fake without having to
    import the real library. Matches youtube-transcript-api >= 1.0 API.
    """

    def list(self, video_id: str): ...  # noqa: ANN201, A003


class YouTubeTranscriptClient:
    """Fetch transcripts for a single YouTube video.

    Args:
        fetcher: Optional `_TranscriptFetcher`. Defaults to a real
            `youtube_transcript_api.YouTubeTranscriptApi` instance.
    """

    def __init__(self, fetcher: _TranscriptFetcher | None = None) -> None:
        self._fetcher: _TranscriptFetcher | None = fetcher

    def _load_fetcher(self) -> _TranscriptFetcher:
        if self._fetcher is not None:
            return self._fetcher
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover — env-level failure
            raise YouTubeError(
                "youtube-transcript-api is not installed. "
                "Run `pip install youtube-transcript-api`."
            ) from exc
        # 1.x requires instantiation; 0.x accepted classmethod calls.
        # We target 1.x (see pyproject `youtube-transcript-api>=1.0`).
        self._fetcher = YouTubeTranscriptApi()
        return self._fetcher

    def fetch(self, request: TranscriptRequest) -> TranscriptResult:
        """Fetch the transcript described by the request."""
        fetcher = self._load_fetcher()
        video_id = extract_video_id(request.source)

        try:
            transcript_list = fetcher.list(video_id)
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc, video_id) from exc

        transcript = self._pick_transcript(transcript_list, request)
        try:
            raw = transcript.fetch()
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc, video_id) from exc

        segments = [_parse_segment(item) for item in raw]

        return TranscriptResult(
            video_id=video_id,
            language=getattr(transcript, "language_code", request.languages[0]),
            is_generated=bool(getattr(transcript, "is_generated", False)),
            segments=segments,
            fetched_at=datetime.now(tz=UTC),
        )

    def _pick_transcript(self, transcript_list, request: TranscriptRequest):  # noqa: ANN001
        """Pick the best transcript from the available list.

        Preference order:
          1. Manual transcripts in one of `request.languages`.
          2. Auto-generated transcripts in one of `request.languages` (if allowed).
          3. Raise if neither is available.
        """
        # list_transcripts returns an iterable of Transcript objects; some
        # versions expose .find_manually_created_transcript / .find_generated_transcript.
        try:
            return transcript_list.find_manually_created_transcript(request.languages)
        except Exception:  # noqa: BLE001
            pass

        if request.allow_generated:
            try:
                return transcript_list.find_generated_transcript(request.languages)
            except Exception as exc:  # noqa: BLE001
                raise YouTubeError(
                    f"No transcript available for languages={request.languages}."
                ) from exc

        raise YouTubeError(
            f"No manual transcript available for languages={request.languages} "
            "and allow_generated is False."
        )

    @staticmethod
    def _map_error(exc: Exception, video_id: str) -> YouTubeError:
        name = type(exc).__name__
        if "TranscriptsDisabled" in name:
            return YouTubeError(f"Transcripts disabled for video {video_id}.")
        if "NoTranscriptFound" in name:
            return YouTubeError(f"No transcript found for video {video_id}.")
        if "VideoUnavailable" in name:
            return YouTubeError(f"Video {video_id} is unavailable.")
        if "TooManyRequests" in name:
            return YouTubeError("YouTube rate-limited the request. Try again later.")
        return YouTubeError(f"{name}: {exc}")


def _parse_segment(item) -> TranscriptSegment:  # noqa: ANN001
    """Normalise a segment dict (or object) to TranscriptSegment.

    youtube-transcript-api ≥ 0.6 returns dicts with keys
    {text, start, duration}. Older / fork versions sometimes return
    objects with attributes of the same name.
    """
    if isinstance(item, dict):
        return TranscriptSegment(
            text=item.get("text", ""),
            start=float(item.get("start", 0.0)),
            duration=float(item.get("duration", 0.0)),
        )
    return TranscriptSegment(
        text=getattr(item, "text", ""),
        start=float(getattr(item, "start", 0.0)),
        duration=float(getattr(item, "duration", 0.0)),
    )
