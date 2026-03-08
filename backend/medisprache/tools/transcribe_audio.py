from __future__ import annotations

import mimetypes
import os
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel
from google.adk.tools.tool_context import ToolContext

from medisprache.schemas.transcript import TranscriptResult

# Lighter defaults for 8GB RAM; override with env for more capable machines.
_DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "base")
_DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
_DEFAULT_BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "3"))  # 3 uses less memory than 5
_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

# Valid faster-whisper model sizes (LLM sometimes passes tool name or invalid value).
_VALID_WHISPER_MODELS = frozenset({
    "tiny.en", "tiny", "base.en", "base", "small.en", "small",
    "medium.en", "medium", "large-v1", "large-v2", "large-v3", "large",
    "distil-large-v2", "distil-medium.en", "distil-small.en",
    "distil-large-v3", "distil-large-v3.5", "large-v3-turbo", "turbo",
})
# HuggingFace-style names map to the same size.
_VALID_WHISPER_MODELS |= {
    f"Systran/faster-whisper-{s}" for s in ("tiny", "base", "small", "medium", "large-v2", "large-v3")
}

_model_cache: dict[str, WhisperModel] = {}


def _normalize_model_name(model_name: str) -> str:
    """Return a valid Whisper model name; use default if LLM passed invalid value (e.g. 'transcribe')."""
    if not model_name or not model_name.strip():
        return _DEFAULT_MODEL
    candidate = model_name.strip()
    if candidate in _VALID_WHISPER_MODELS:
        return candidate
    # Allow HuggingFace path that ends with a known size.
    for valid in _VALID_WHISPER_MODELS:
        if candidate == valid or candidate.endswith("/" + valid):
            return candidate
    return _DEFAULT_MODEL


def _normalize_device(device: str) -> str:
    """Use env default when LLM requests CUDA but we're in a CPU-only environment (e.g. Docker)."""
    if not device or not device.strip():
        return _DEFAULT_DEVICE
    d = device.strip().lower()
    if d.startswith("cuda"):
        return _DEFAULT_DEVICE  # Respect WHISPER_DEVICE=cpu in Docker / 8GB
    return d if d in ("cpu", "auto") else _DEFAULT_DEVICE


def _get_model(model_name: str, device: str) -> WhisperModel:
    """Return a cached WhisperModel, loading on first call."""
    model_name = _normalize_model_name(model_name)
    key = f"{model_name}:{device}"
    if key not in _model_cache:
        compute_type = "int8" if device == "cpu" else "float16"
        _model_cache[key] = WhisperModel(model_name, device=device, compute_type=compute_type)
    return _model_cache[key]


def _transcribe_path(
    audio_path: Path,
    *,
    model_name: str,
    device: str,
    language: str | None,
    beam_size: int,
) -> TranscriptResult:
    """Run transcription on a local audio path and return a validated model."""
    model_name = _normalize_model_name(model_name)
    device = _normalize_device(device)
    if beam_size < 1:
        raise ValueError("beam_size must be >= 1")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = _get_model(model_name, device)
    segments_gen, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
    )

    segments = []
    full_text_parts: list[str] = []
    duration = 0.0

    for seg in segments_gen:
        text = seg.text.strip()
        segments.append({"start": seg.start, "end": seg.end, "text": text})
        if text:
            full_text_parts.append(text)
        duration = seg.end

    return TranscriptResult(
        text=" ".join(full_text_parts).strip(),
        segments=segments,
        language=info.language,
        model_name=model_name,
        duration_seconds=duration,
    )


def _looks_like_audio_artifact(filename: str) -> bool:
    return Path(filename).suffix.lower() in _AUDIO_EXTENSIONS


def _pick_artifact_name(
    artifact_names: list[str],
    requested_name: str | None,
) -> str:
    if requested_name:
        if requested_name not in artifact_names:
            raise ValueError(
                f"Artifact '{requested_name}' is not available in this session."
            )
        return requested_name

    for candidate in reversed(artifact_names):
        if _looks_like_audio_artifact(candidate):
            return candidate

    if artifact_names:
        return artifact_names[-1]

    raise ValueError("No uploaded artifacts are available in this session.")


def _suffix_for_artifact(filename: str, mime_type: str | None) -> str:
    suffix = Path(filename).suffix
    if suffix:
        return suffix
    guessed = mimetypes.guess_extension(mime_type or "")
    return guessed or ".bin"


def transcribe_audio(
    audio_path: str,
    *,
    model_name: str = _DEFAULT_MODEL,
    device: str = _DEFAULT_DEVICE,
    language: str | None = "de",
    beam_size: int = _DEFAULT_BEAM_SIZE,
) -> dict[str, object]:
    """Transcribe *audio_path* and return a dict matching ``TranscriptResult``.

    Uses faster-whisper (CTranslate2), so no PyTorch is needed.
    Defaults to Systran/faster-whisper-small with German language forcing.
    """
    result = _transcribe_path(
        Path(audio_path),
        model_name=model_name,
        device=device,
        language=language,
        beam_size=beam_size,
    )
    return result.model_dump()


def transcribe_audio_file(
    audio_path: str,
    *,
    model_name: str = _DEFAULT_MODEL,
    device: str = _DEFAULT_DEVICE,
    language: str | None = "de",
    beam_size: int = _DEFAULT_BEAM_SIZE,
) -> dict[str, object]:
    """Transcribe a server-local German medical dictation file.

    Use this tool when the user gives a filesystem path that exists inside the
    backend container or local backend environment.
    """
    return transcribe_audio(
        audio_path,
        model_name=model_name,
        device=device,
        language=language,
        beam_size=beam_size,
    )


async def transcribe_uploaded_artifact(
    artifact_name: str | None = None,
    *,
    tool_context: ToolContext,
    model_name: str = _DEFAULT_MODEL,
    device: str = _DEFAULT_DEVICE,
    language: str | None = "de",
    beam_size: int = _DEFAULT_BEAM_SIZE,
) -> dict[str, object]:
    """Transcribe an uploaded audio artifact from the current ADK session.

    Use this tool when the user uploads an MP3 or WAV file through the frontend.
    If ``artifact_name`` is omitted, the most recent audio-like artifact in the
    session is selected automatically.
    """
    artifact_names = await tool_context.list_artifacts()
    selected_name = _pick_artifact_name(artifact_names, artifact_name)
    artifact = await tool_context.load_artifact(selected_name)
    if artifact is None or artifact.inline_data is None:
        raise ValueError(
            f"Artifact '{selected_name}' is missing or does not contain inline audio data."
        )

    temp_path: Path | None = None
    try:
        suffix = _suffix_for_artifact(
            selected_name,
            artifact.inline_data.mime_type,
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(artifact.inline_data.data)
            temp_path = Path(handle.name)

        result = _transcribe_path(
            temp_path,
            model_name=model_name,
            device=device,
            language=language,
            beam_size=beam_size,
        ).model_dump()
        result["artifact_name"] = selected_name
        return result
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
