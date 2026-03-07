from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    pipeline as hf_pipeline,
)

from medisprache.schemas.transcript import TranscriptResult

_MULTIMED_REPO = "leduckhai/MultiMed-ST"
_MULTIMED_MODEL_SUB = "asr/whisper-small-german/checkpoint"
_MULTIMED_PROCESSOR_SUB = "asr/whisper-small-german"

_DEFAULT_MODEL = os.getenv("WHISPER_MODEL", _MULTIMED_REPO)
_DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

_pipe_cache: dict[str, Any] = {}


def _get_pipeline(model_name: str, device: str) -> Any:
    """Return a cached HuggingFace ASR pipeline, loading the model on first call."""
    cache_key = f"{model_name}:{device}"
    if cache_key not in _pipe_cache:
        if model_name == _MULTIMED_REPO:
            # MultiMed stores model weights and tokenizer in separate subfolders.
            model = WhisperForConditionalGeneration.from_pretrained(
                _MULTIMED_REPO, subfolder=_MULTIMED_MODEL_SUB,
            )
            processor = WhisperProcessor.from_pretrained(
                _MULTIMED_REPO, subfolder=_MULTIMED_PROCESSOR_SUB,
            )
            pipe = hf_pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                device=device,
            )
        else:
            pipe = hf_pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=device,
            )
        _pipe_cache[cache_key] = pipe
    return _pipe_cache[cache_key]


def transcribe_audio(
    audio_path: str | Path,
    *,
    model_name: str = _DEFAULT_MODEL,
    device: str = _DEFAULT_DEVICE,
    language: str | None = "de",
    beam_size: int = 5,
) -> dict[str, object]:
    """Transcribe *audio_path* and return a dict matching ``TranscriptResult``.

    Uses a HuggingFace Whisper pipeline.  Defaults to the MultiMed
    Whisper-Small-German model, which is fine-tuned on medical German speech.

    Parameters
    ----------
    audio_path:
        Path to any audio file accepted by soundfile / ffmpeg.
    model_name:
        HuggingFace repo id or local path.  Defaults to the MultiMed
        Whisper-Small-German model (``leduckhai/MultiMed-ST``).
    device:
        ``"cpu"`` or ``"cuda"``.
    language:
        BCP-47 language code hint.  Defaults to ``"de"`` for German medical
        dictation.  Pass ``None`` to let the model auto-detect.
    beam_size:
        Beam search width — higher is slower but more accurate.

    Returns
    -------
    dict[str, object]
        Validated against ``TranscriptResult`` before being returned.

    Raises
    ------
    FileNotFoundError
        If *audio_path* does not exist.
    ValueError
        If *beam_size* is less than 1.
    """
    if beam_size < 1:
        raise ValueError("beam_size must be >= 1")

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio_data, sample_rate = sf.read(str(audio_path), dtype="float32")
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)
    duration = len(audio_data) / sample_rate

    pipe = _get_pipeline(model_name, device)

    generate_kwargs: dict[str, object] = {"num_beams": beam_size}
    if language is not None:
        generate_kwargs["language"] = language

    output = pipe(
        {"raw": audio_data, "sampling_rate": sample_rate},
        return_timestamps=True,
        generate_kwargs=generate_kwargs,
    )

    segments = []
    full_text_parts: list[str] = []

    for chunk in output.get("chunks", []):
        start, end = chunk["timestamp"]
        text = chunk["text"].strip()
        segments.append({
            "start": start if start is not None else 0.0,
            "end": end if end is not None else duration,
            "text": text,
        })
        if text:
            full_text_parts.append(text)

    result = TranscriptResult(
        text=" ".join(full_text_parts).strip(),
        segments=segments,
        language=language,
        model_name=model_name,
        duration_seconds=duration,
    )
    return result.model_dump()
