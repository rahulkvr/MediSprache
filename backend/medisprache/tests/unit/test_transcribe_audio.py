from __future__ import annotations

import medisprache.tools.transcribe_audio as transcribe_module
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


def test_resolve_runtime_device_uses_cuda_when_available(monkeypatch):
    monkeypatch.setattr(transcribe_module, "_cuda_device_count", lambda: 1)
    assert transcribe_module._resolve_runtime_device("auto") == "cuda"


def test_resolve_runtime_device_falls_back_to_cpu_when_no_cuda(monkeypatch):
    monkeypatch.setattr(transcribe_module, "_cuda_device_count", lambda: 0)
    assert transcribe_module._resolve_runtime_device("auto") == "cpu"
    assert transcribe_module._resolve_runtime_device("cuda") == "cpu"
