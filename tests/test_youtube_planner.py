"""Tests for the high-level fetch_transcript planner."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from kit.youtube.core import TranscriptRequest, TranscriptResult, TranscriptSegment
from kit.youtube.planner import fetch_transcript


def _fake_result() -> TranscriptResult:
    return TranscriptResult(
        video_id="dQw4w9WgXcQ",
        language="en",
        is_generated=False,
        segments=[TranscriptSegment(start=0.0, duration=1.0, text="hi")],
        fetched_at=datetime(2026, 4, 18, tzinfo=UTC),
    )


class TestFetchTranscript:
    def test_delegates_to_client(self):
        mock_client = MagicMock()
        mock_client.fetch.return_value = _fake_result()
        request = TranscriptRequest(source="dQw4w9WgXcQ")

        result = fetch_transcript(request, client=mock_client)

        mock_client.fetch.assert_called_once_with(request)
        assert result.video_id == "dQw4w9WgXcQ"

    def test_returns_client_result_unchanged(self):
        mock_client = MagicMock()
        expected = _fake_result()
        mock_client.fetch.return_value = expected

        assert fetch_transcript(
            TranscriptRequest(source="dQw4w9WgXcQ"),
            client=mock_client,
        ) is expected
