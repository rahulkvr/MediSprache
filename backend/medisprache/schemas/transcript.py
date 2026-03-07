from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


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