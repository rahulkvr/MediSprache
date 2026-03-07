from __future__ import annotations

from pathlib import Path

import pytest

from medisprache.schemas.transcript import TranscriptResult
from medisprache.tools.transcribe_audio import transcribe_audio

SAMPLE_AUDIO = (
    Path(__file__).parents[2] / "fixtures" / "sample_audio" / "sample_01_bronchitis.mp3"
)


def test_sample_audio_fixture_exists():
    assert SAMPLE_AUDIO.exists(), f"Sample audio not found at {SAMPLE_AUDIO}"


@pytest.mark.integration
def test_transcribe_audio_happy_path():
    result = transcribe_audio(SAMPLE_AUDIO)

    assert isinstance(result, dict)

    validated = TranscriptResult(**result)
    assert validated.text.strip(), "Transcript text must not be empty"
    assert validated.model_name == "leduckhai/MultiMed-ST"
    assert isinstance(validated.segments, list)
    assert len(validated.segments) > 0
