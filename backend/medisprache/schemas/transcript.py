from __future__ import annotations

from typing import List, Optional

from medisprache.schemas.base import StrictBaseModel


class TranscriptSegment(StrictBaseModel):
    start: float
    end: float
    text: str


class TranscriptResult(StrictBaseModel):
    text: str
    segments: List[TranscriptSegment]
    language: Optional[str] = None
    model_name: str
    duration_seconds: Optional[float] = None