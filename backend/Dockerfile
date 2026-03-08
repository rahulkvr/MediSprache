# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && apt-get install -y --no-install-recommends ffmpeg

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY . .

# Pre-download the configured Whisper model at build time.
# Pass WHISPER_MODEL as a build arg so the warmed cache matches runtime.
ARG WHISPER_MODEL=base
RUN --mount=type=cache,target=/root/.cache/huggingface \
    WHISPER_MODEL="${WHISPER_MODEL}" uv run python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8')"

EXPOSE 8000

CMD ["uv", "run", "adk", "api_server", "--host", "0.0.0.0", "--port", "8000"]
