"""Tests for the kit_youtube_transcript MCP tool."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from kit.config import KitConfig
from kit.youtube.core import TranscriptRequest, TranscriptResult, TranscriptSegment


@pytest.fixture
def mock_config():
    return KitConfig()


def _sample_result() -> TranscriptResult:
    return TranscriptResult(
        video_id="dQw4w9WgXcQ",
        language="en",
        is_generated=False,
        segments=[
            TranscriptSegment(start=0.0, duration=1.5, text="hello"),
            TranscriptSegment(start=1.5, duration=2.0, text="world"),
        ],
        fetched_at=datetime(2026, 4, 18, 12, 0, tzinfo=UTC),
    )


class TestKitYoutubeTranscript:
    @patch("kit.youtube.mcp_tools.fetch_transcript")
    def test_returns_json(self, mock_fetch, mock_config):
        mock_fetch.return_value = _sample_result()

        from mcp.server.fastmcp import FastMCP

        from kit.youtube.mcp_tools import register_youtube_tools

        mcp = FastMCP("test")
        register_youtube_tools(mcp, mock_config)

        tool_fn = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "kit_youtube_transcript":
                tool_fn = tool.fn
                break

        assert tool_fn is not None, "kit_youtube_transcript not registered"

        raw = tool_fn(source="https://youtu.be/dQw4w9WgXcQ")
        payload = json.loads(raw)

        assert payload["video_id"] == "dQw4w9WgXcQ"
        assert payload["language"] == "en"
        assert payload["is_generated"] is False
        assert len(payload["segments"]) == 2
        assert payload["segments"][0]["text"] == "hello"

    @patch("kit.youtube.mcp_tools.fetch_transcript")
    def test_passes_language_preferences(self, mock_fetch, mock_config):
        mock_fetch.return_value = _sample_result()

        from mcp.server.fastmcp import FastMCP

        from kit.youtube.mcp_tools import register_youtube_tools

        mcp = FastMCP("test")
        register_youtube_tools(mcp, mock_config)

        tool_fn = next(
            t.fn for t in mcp._tool_manager._tools.values()
            if t.name == "kit_youtube_transcript"
        )

        tool_fn(source="dQw4w9WgXcQ", languages=["de", "en"], allow_generated=False)

        call = mock_fetch.call_args
        passed_request: TranscriptRequest = call.args[0]
        assert passed_request.languages == ["de", "en"]
        assert passed_request.allow_generated is False

    @patch("kit.youtube.mcp_tools.fetch_transcript")
    def test_default_languages_when_none_passed(self, mock_fetch, mock_config):
        mock_fetch.return_value = _sample_result()

        from mcp.server.fastmcp import FastMCP

        from kit.youtube.mcp_tools import register_youtube_tools

        mcp = FastMCP("test")
        register_youtube_tools(mcp, mock_config)

        tool_fn = next(
            t.fn for t in mcp._tool_manager._tools.values()
            if t.name == "kit_youtube_transcript"
        )

        tool_fn(source="dQw4w9WgXcQ")

        passed_request: TranscriptRequest = mock_fetch.call_args.args[0]
        assert passed_request.languages == ["en"]
