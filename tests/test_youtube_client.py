"""Tests for the YouTubeTranscriptClient.

Uses fake fetcher/transcript-list/transcript classes so the tests don't
depend on the real youtube-transcript-api library. A separate smoke test
(marked @pytest.mark.smoke) hits a real YouTube video.
"""

from __future__ import annotations

from typing import Any

import pytest

from kit.errors import YouTubeError
from kit.youtube.client import YouTubeTranscriptClient
from kit.youtube.core import TranscriptRequest

# --- Fakes -----------------------------------------------------------------


class _FakeTranscript:
    def __init__(
        self,
        segments: list[dict[str, Any]],
        language_code: str = "en",
        is_generated: bool = False,
    ) -> None:
        self._segments = segments
        self.language_code = language_code
        self.is_generated = is_generated

    def fetch(self) -> list[dict[str, Any]]:
        return list(self._segments)


class _FakeTranscriptList:
    def __init__(
        self,
        manual: dict[str, _FakeTranscript] | None = None,
        generated: dict[str, _FakeTranscript] | None = None,
    ) -> None:
        self._manual = manual or {}
        self._generated = generated or {}

    def find_manually_created_transcript(self, languages: list[str]) -> _FakeTranscript:
        for lang in languages:
            if lang in self._manual:
                return self._manual[lang]
        raise _NoTranscriptFound("manual", languages)

    def find_generated_transcript(self, languages: list[str]) -> _FakeTranscript:
        for lang in languages:
            if lang in self._generated:
                return self._generated[lang]
        raise _NoTranscriptFound("generated", languages)


class _FakeFetcher:
    def __init__(self, transcript_list: _FakeTranscriptList | Exception) -> None:
        self._state = transcript_list

    def list(self, video_id: str):  # noqa: ANN201, A003
        if isinstance(self._state, Exception):
            raise self._state
        return self._state


class _NoTranscriptFound(Exception):  # noqa: N818
    """Mimics youtube_transcript_api.NoTranscriptFound by name (matched by substring)."""


class _TranscriptsDisabled(Exception):  # noqa: N818
    """Mimics youtube_transcript_api.TranscriptsDisabled by name (matched by substring)."""


class _VideoUnavailable(Exception):  # noqa: N818
    """Mimics youtube_transcript_api.VideoUnavailable by name (matched by substring)."""


# --- Tests -----------------------------------------------------------------


def _segments() -> list[dict[str, Any]]:
    return [
        {"text": "hello", "start": 0.0, "duration": 1.5},
        {"text": "world", "start": 1.5, "duration": 2.0},
    ]


class TestFetchSuccess:
    def test_prefers_manual_transcript(self):
        manual = _FakeTranscript(_segments(), language_code="en", is_generated=False)
        generated = _FakeTranscript(
            [{"text": "auto", "start": 0.0, "duration": 1.0}],
            language_code="en",
            is_generated=True,
        )
        fetcher = _FakeFetcher(
            _FakeTranscriptList(manual={"en": manual}, generated={"en": generated})
        )
        client = YouTubeTranscriptClient(fetcher=fetcher)

        result = client.fetch(TranscriptRequest(source="dQw4w9WgXcQ"))

        assert result.video_id == "dQw4w9WgXcQ"
        assert result.language == "en"
        assert result.is_generated is False
        assert [s.text for s in result.segments] == ["hello", "world"]

    def test_falls_back_to_generated_when_manual_missing(self):
        generated = _FakeTranscript(_segments(), language_code="en", is_generated=True)
        fetcher = _FakeFetcher(_FakeTranscriptList(generated={"en": generated}))
        client = YouTubeTranscriptClient(fetcher=fetcher)

        result = client.fetch(TranscriptRequest(source="dQw4w9WgXcQ"))

        assert result.is_generated is True
        assert result.language == "en"

    def test_respects_language_priority(self):
        de = _FakeTranscript(
            [{"text": "hallo", "start": 0.0, "duration": 1.0}],
            language_code="de",
        )
        en = _FakeTranscript(_segments(), language_code="en")
        fetcher = _FakeFetcher(_FakeTranscriptList(manual={"de": de, "en": en}))
        client = YouTubeTranscriptClient(fetcher=fetcher)

        result = client.fetch(
            TranscriptRequest(source="dQw4w9WgXcQ", languages=["de", "en"])
        )

        assert result.language == "de"
        assert result.segments[0].text == "hallo"

    def test_returns_parsed_durations(self):
        manual = _FakeTranscript(_segments(), language_code="en")
        fetcher = _FakeFetcher(_FakeTranscriptList(manual={"en": manual}))
        client = YouTubeTranscriptClient(fetcher=fetcher)

        result = client.fetch(TranscriptRequest(source="dQw4w9WgXcQ"))

        assert result.total_duration == pytest.approx(3.5)


class TestFetchFailures:
    def test_rejects_when_allow_generated_false_and_only_generated_exists(self):
        generated = _FakeTranscript(_segments(), is_generated=True)
        fetcher = _FakeFetcher(_FakeTranscriptList(generated={"en": generated}))
        client = YouTubeTranscriptClient(fetcher=fetcher)

        with pytest.raises(YouTubeError, match="No manual transcript"):
            client.fetch(
                TranscriptRequest(source="dQw4w9WgXcQ", allow_generated=False)
            )

    def test_no_transcript_in_requested_language(self):
        manual = _FakeTranscript(_segments(), language_code="de")
        fetcher = _FakeFetcher(_FakeTranscriptList(manual={"de": manual}))
        client = YouTubeTranscriptClient(fetcher=fetcher)

        with pytest.raises(YouTubeError):
            client.fetch(
                TranscriptRequest(source="dQw4w9WgXcQ", languages=["ja", "fr"])
            )

    def test_maps_transcripts_disabled(self):
        fetcher = _FakeFetcher(_TranscriptsDisabled())
        client = YouTubeTranscriptClient(fetcher=fetcher)

        with pytest.raises(YouTubeError, match="Transcripts disabled"):
            client.fetch(TranscriptRequest(source="dQw4w9WgXcQ"))

    def test_maps_video_unavailable(self):
        fetcher = _FakeFetcher(_VideoUnavailable())
        client = YouTubeTranscriptClient(fetcher=fetcher)

        with pytest.raises(YouTubeError, match="unavailable"):
            client.fetch(TranscriptRequest(source="dQw4w9WgXcQ"))

    def test_maps_unknown_errors(self):
        fetcher = _FakeFetcher(RuntimeError("boom"))
        client = YouTubeTranscriptClient(fetcher=fetcher)

        with pytest.raises(YouTubeError, match="RuntimeError"):
            client.fetch(TranscriptRequest(source="dQw4w9WgXcQ"))


@pytest.mark.smoke
class TestSmoke:
    """Hits the real youtube-transcript-api library + YouTube.

    Skipped in CI via `-m "not smoke"`. Run explicitly when you want to
    verify end-to-end. Uses Rick Astley — famously stable video.
    """

    def test_real_video_fetch(self):
        client = YouTubeTranscriptClient()
        result = client.fetch(
            TranscriptRequest(source="dQw4w9WgXcQ", languages=["en"])
        )
        assert result.video_id == "dQw4w9WgXcQ"
        assert len(result.segments) > 0
        assert "never" in result.plain_text.lower() or len(result.plain_text) > 50
