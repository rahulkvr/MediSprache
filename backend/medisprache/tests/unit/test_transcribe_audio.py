from __future__ import annotations

import pytest

from medisprache.tools.transcribe_audio import transcribe_audio


def test_transcribe_audio_missing_file_raises():
    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        transcribe_audio("/nonexistent/path/audio.mp3")


def test_transcribe_audio_invalid_beam_size_raises():
    with pytest.raises(ValueError, match="beam_size must be >= 1"):
        transcribe_audio(
            "/nonexistent/path/audio.mp3",
            beam_size=0,
        )
