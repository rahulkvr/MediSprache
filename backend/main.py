from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a German medical dictation and print JSON."
    )
    parser.add_argument("audio_path", help="Path to a WAV or MP3 file on disk.")
    parser.add_argument(
        "--llm-provider",
        dest="llm_provider",
        choices=["ollama", "gemini"],
        help="Summary provider: ollama or gemini.",
    )
    parser.add_argument(
        "--ollama-api-base",
        dest="ollama_api_base",
        help="Ollama API base URL, e.g. http://localhost:11434",
    )
    parser.add_argument(
        "--google-api-key",
        dest="google_api_key",
        help="Gemini API key (alternative to GOOGLE_API_KEY env var).",
    )
    parser.add_argument(
        "--whisper-model",
        dest="whisper_model",
        help="Override the speech-to-text model name or local path.",
    )
    parser.add_argument(
        "--whisper-device",
        dest="whisper_device",
        help="Speech-to-text runtime device, e.g. cpu or cuda.",
    )
    return parser.parse_args()


async def run_cli(audio_path: str) -> None:
    from google.adk.artifacts.in_memory_artifact_service import (
        InMemoryArtifactService,
    )
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    from medisprache import app
    from medisprache.schemas.clinical_summary import CompactClinicalSummary

    user_id = "cli"
    session_id = str(uuid.uuid4())
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    await session_service.create_session(
        app_name=app.name,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        app=app,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    prompt = (
        f'Transcribe and summarize the audio file at "{audio_path}". '
        "Use the server-local file tool and respond with JSON only."
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if (
            event.author != "user"
            and event.is_final_response()
            and event.content
            and event.content.parts
        ):
            candidate = "".join(part.text or "" for part in event.content.parts).strip()
            if candidate:
                final_text = candidate

    if not final_text:
        raise RuntimeError("The agent did not produce a final JSON response.")

    summary = CompactClinicalSummary.model_validate_json(final_text)
    print(
        json.dumps(
            summary.model_dump(exclude_none=True),
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    args = parse_args()
    env_updates = {
        "LLM_PROVIDER": args.llm_provider,
        "OLLAMA_API_BASE": args.ollama_api_base,
        "GOOGLE_API_KEY": args.google_api_key,
        "WHISPER_MODEL": args.whisper_model,
        "WHISPER_DEVICE": args.whisper_device,
    }
    for key, value in env_updates.items():
        if value:
            os.environ[key] = value

    asyncio.run(run_cli(args.audio_path))


if __name__ == "__main__":
    main()
