"""Kit YouTube — transcript fetcher.

Public surface:

    from kit.youtube import fetch_transcript, TranscriptRequest

CLI: `kit youtube transcript <url-or-id>`.
MCP: `kit_youtube_transcript`.
"""

from __future__ import annotations

from kit.youtube.core import (
    TranscriptRequest,
    TranscriptResult,
    TranscriptSegment,
    extract_video_id,
)
from kit.youtube.planner import fetch_transcript

__all__ = [
    "TranscriptRequest",
    "TranscriptResult",
    "TranscriptSegment",
    "extract_video_id",
    "fetch_transcript",
]
