"""MCP tool registrations for YouTube transcripts."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from kit.config import KitConfig
from kit.youtube.core import TranscriptRequest
from kit.youtube.planner import fetch_transcript


def register_youtube_tools(mcp: FastMCP, config: KitConfig) -> None:
    """Register YouTube transcript tools on the given FastMCP server."""

    @mcp.tool()
    def kit_youtube_transcript(
        source: str,
        languages: list[str] | None = None,
        allow_generated: bool = True,
    ) -> str:
        """Fetch the transcript for a YouTube video.

        Works without an API key — uses the public transcripts that YouTube
        surfaces alongside the video. No OAuth, no Google account.

        Args:
            source: YouTube URL (any common form) or raw 11-char video ID.
            languages: Preferred language codes in priority order; first
                available wins. Defaults to ['en'].
            allow_generated: If True (default), fall back to auto-generated
                transcripts when no manual one exists.

        Returns:
            JSON string with the full transcript: metadata + segment list
            ({start, duration, text}). Use the `plain_text` property on the
            deserialized result for a concatenated form.
        """
        request = TranscriptRequest(
            source=source,
            languages=languages or ["en"],
            allow_generated=allow_generated,
        )
        result = fetch_transcript(request)
        return result.model_dump_json(indent=2)
