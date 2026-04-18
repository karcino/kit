"""Tests for YouTube core models and URL parsing."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kit.youtube.core import (
    TranscriptRequest,
    TranscriptResult,
    TranscriptSegment,
    extract_video_id,
)


class TestExtractVideoId:
    def test_raw_id_passes_through(self):
        assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_id_with_underscore_and_hyphen(self):
        assert extract_video_id("a_B-cD12_34") == "a_B-cD12_34"

    def test_watch_url(self):
        assert (
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_watch_url_with_extra_params(self):
        assert (
            extract_video_id(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&feature=shared"
            )
            == "dQw4w9WgXcQ"
        )

    def test_short_youtu_be(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_youtu_be_with_query(self):
        assert (
            extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=30") == "dQw4w9WgXcQ"
        )

    def test_shorts(self):
        assert (
            extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_embed(self):
        assert (
            extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_mobile(self):
        assert (
            extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_music(self):
        assert (
            extract_video_id("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_strips_whitespace(self):
        assert extract_video_id("  dQw4w9WgXcQ  ") == "dQw4w9WgXcQ"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="Empty"):
            extract_video_id("")

    def test_rejects_bogus_url(self):
        with pytest.raises(ValueError, match="Could not extract"):
            extract_video_id("https://vimeo.com/12345")

    def test_rejects_short_id(self):
        with pytest.raises(ValueError, match="Could not extract"):
            extract_video_id("short")

    def test_rejects_long_id(self):
        with pytest.raises(ValueError, match="Could not extract"):
            extract_video_id("thisidiswaytoolong")


class TestTranscriptRequest:
    def test_accepts_url(self):
        req = TranscriptRequest(source="https://youtu.be/dQw4w9WgXcQ")
        assert req.video_id == "dQw4w9WgXcQ"

    def test_accepts_raw_id(self):
        req = TranscriptRequest(source="dQw4w9WgXcQ")
        assert req.video_id == "dQw4w9WgXcQ"

    def test_default_languages(self):
        req = TranscriptRequest(source="dQw4w9WgXcQ")
        assert req.languages == ["en"]

    def test_custom_languages(self):
        req = TranscriptRequest(source="dQw4w9WgXcQ", languages=["de", "en"])
        assert req.languages == ["de", "en"]

    def test_allow_generated_default_true(self):
        req = TranscriptRequest(source="dQw4w9WgXcQ")
        assert req.allow_generated is True

    def test_rejects_invalid_source(self):
        with pytest.raises(ValueError):
            TranscriptRequest(source="not-a-youtube-url")


class TestTranscriptSegment:
    def test_end_computes_correctly(self):
        seg = TranscriptSegment(start=10.0, duration=2.5, text="hello")
        assert seg.end == 12.5


class TestTranscriptResult:
    def _make_result(self, segments: list[TranscriptSegment]) -> TranscriptResult:
        return TranscriptResult(
            video_id="dQw4w9WgXcQ",
            language="en",
            is_generated=False,
            segments=segments,
            fetched_at=datetime(2026, 4, 18, 12, 0, tzinfo=UTC),
        )

    def test_total_duration_empty(self):
        assert self._make_result([]).total_duration == 0.0

    def test_total_duration_single_segment(self):
        result = self._make_result([
            TranscriptSegment(start=0.0, duration=3.0, text="hello")
        ])
        assert result.total_duration == 3.0

    def test_total_duration_uses_last_segment_end(self):
        result = self._make_result([
            TranscriptSegment(start=0.0, duration=2.0, text="a"),
            TranscriptSegment(start=2.0, duration=3.5, text="b"),
            TranscriptSegment(start=5.5, duration=1.5, text="c"),
        ])
        assert result.total_duration == 7.0

    def test_plain_text_joins_segments(self):
        result = self._make_result([
            TranscriptSegment(start=0.0, duration=1.0, text="hello"),
            TranscriptSegment(start=1.0, duration=1.0, text="world"),
        ])
        assert result.plain_text == "hello world"

    def test_plain_text_empty(self):
        assert self._make_result([]).plain_text == ""
