"""High-level YouTube transcript API."""

from __future__ import annotations

from kit.youtube.client import YouTubeTranscriptClient
from kit.youtube.core import TranscriptRequest, TranscriptResult


def fetch_transcript(
    request: TranscriptRequest,
    client: YouTubeTranscriptClient | None = None,
) -> TranscriptResult:
    """Fetch a transcript for a YouTube video.

    Args:
        request: TranscriptRequest with source (URL or ID) and language prefs.
        client: Optional pre-built client (for tests).

    Returns:
        TranscriptResult with every segment plus metadata.
    """
    client = client or YouTubeTranscriptClient()
    return client.fetch(request)
