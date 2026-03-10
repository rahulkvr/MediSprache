from __future__ import annotations

import os
import re
from pathlib import Path
from typing import AsyncGenerator

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.context import Context
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps.app import App
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.adk.models.lite_llm import LiteLlm
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin
from google.genai import types

from medisprache.prompts import build_schema_instruction, get_prompt_profile
from medisprache.prompts.registry import COMPACT_CLINICAL_SUMMARY_PROMPT_ID
from medisprache.schemas.clinical_summary import CompactClinicalSummary
from medisprache.tools.transcribe_audio import transcribe_audio, transcribe_uploaded_artifact

APP_NAME = "medisprache"
SUPPORTED_LLM_PROVIDERS = {"ollama", "gemini"}
FIXED_OLLAMA_MODEL = "qwen2.5:1.5b"
FIXED_GEMINI_MODEL = "gemini-3-flash-preview"
DEFAULT_OLLAMA_API_BASE = "http://localhost:11434"
GEMINI_THINKING_LEVEL = "high"
TRANSCRIPT_STATE_KEY = "transcript_text"
SUMMARY_STATE_KEY = "clinical_summary"
SUMMARY_PROMPT_ID = os.getenv("SUMMARY_PROMPT_ID", COMPACT_CLINICAL_SUMMARY_PROMPT_ID)
GEMINI_RESPONSE_JSON_SCHEMA = CompactClinicalSummary.model_json_schema()

SUMMARY_INSTRUCTION = build_schema_instruction(
    schema_model=CompactClinicalSummary,
    config=get_prompt_profile(SUMMARY_PROMPT_ID),
    transcript_state_key=TRANSCRIPT_STATE_KEY,
)


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    stripped = value.strip()
    return stripped or None


def _resolve_llm_provider() -> str:
    provider = _get_env("LLM_PROVIDER")
    if not provider:
        raise ValueError(
            "LLM_PROVIDER is required. Set it to 'ollama' or 'gemini'."
        )

    normalized = provider.lower()
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        allowed = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Allowed values: {allowed}."
        )
    return normalized


def _validate_fixed_model_env_overrides() -> None:
    fixed_env_values = {
        "OLLAMA_MODEL": FIXED_OLLAMA_MODEL,
        "GEMINI_MODEL": FIXED_GEMINI_MODEL,
    }
    for env_var, fixed_value in fixed_env_values.items():
        configured = _get_env(env_var)
        if configured and configured != fixed_value:
            raise ValueError(
                f"{env_var} is fixed in this app. "
                f"Use '{fixed_value}' or remove {env_var}."
            )


def _build_summary_model(provider: str) -> BaseLlm:
    _validate_fixed_model_env_overrides()

    if provider == "ollama":
        ollama_api_base = _get_env("OLLAMA_API_BASE") or DEFAULT_OLLAMA_API_BASE
        return LiteLlm(
            model=f"ollama_chat/{FIXED_OLLAMA_MODEL}",
            api_base=ollama_api_base,
        )

    if provider == "gemini":
        if not (_get_env("GOOGLE_API_KEY") or _get_env("GEMINI_API_KEY")):
            raise ValueError(
                "Gemini provider selected but no API key configured. "
                "Set GOOGLE_API_KEY or GEMINI_API_KEY."
            )
        return Gemini(model=FIXED_GEMINI_MODEL)

    allowed = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
    raise ValueError(f"Unsupported provider '{provider}'. Allowed values: {allowed}.")


def _build_generate_content_config(provider: str) -> types.GenerateContentConfig:
    if provider == "ollama":
        return types.GenerateContentConfig(temperature=0)

    if provider == "gemini":
        # Use JSON mode + JSON schema for Gemini to improve structure fidelity
        # without relying on ADK output_schema mapping (which currently breaks
        # for this model/API combination).
        return types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=GEMINI_RESPONSE_JSON_SCHEMA,
            thinking_config=types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVEL),
        )

    allowed = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
    raise ValueError(f"Unsupported provider '{provider}'. Allowed values: {allowed}.")


def _build_summary_agent() -> LlmAgent:
    provider = _resolve_llm_provider()
    common_kwargs = dict(
        model=_build_summary_model(provider),
        name="summary_step",
        description="Builds a compact clinical summary JSON from transcript text.",
        instruction=SUMMARY_INSTRUCTION,
        generate_content_config=_build_generate_content_config(provider),
    )

    # Gemini API currently rejects ADK's response_schema payload shape for this
    # strict schema mode. Keep strict schema mode for Ollama and use Gemini
    # response_json_schema in generate_content_config instead.
    if provider == "ollama":
        return LlmAgent(
            **common_kwargs,
            output_schema=CompactClinicalSummary,
            output_key=SUMMARY_STATE_KEY,
        )

    return LlmAgent(**common_kwargs)


def _extract_audio_path_from_user_content(user_content: object | None) -> str | None:
    """Extract a server-local audio path from user text when no artifact exists."""
    if user_content is None:
        return None

    parts = getattr(user_content, "parts", None)
    if not parts:
        return None

    combined_text = " ".join(
        part_text.strip()
        for part in parts
        if (part_text := getattr(part, "text", None))
    )
    if not combined_text:
        return None

    extracted: str | None = None

    quoted_match = re.search(
        r"""[\"']([^\"']+\.(?:mp3|wav|m4a|ogg|flac))[\"']""",
        combined_text,
        flags=re.IGNORECASE,
    )
    if quoted_match:
        extracted = quoted_match.group(1)
    else:
        bare_match = re.search(
            r"""([A-Za-z]:[^\s\"']+\.(?:mp3|wav|m4a|ogg|flac)|/[^\s\"']+\.(?:mp3|wav|m4a|ogg|flac))""",
            combined_text,
            flags=re.IGNORECASE,
        )
        if bare_match:
            extracted = bare_match.group(1).rstrip(".,)")

    if not extracted:
        return None

    return str(Path(extracted).resolve())


class DeterministicTranscriptionAgent(BaseAgent):
    """Directly transcribe uploaded artifact/path without LLM tool selection."""

    output_key: str = TRANSCRIPT_STATE_KEY

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        tool_context = Context(ctx)
        artifact_names = await tool_context.list_artifacts()

        if artifact_names:
            transcription_result = await transcribe_uploaded_artifact(
                tool_context=tool_context
            )
        else:
            audio_path = _extract_audio_path_from_user_content(ctx.user_content)
            if not audio_path:
                raise ValueError(
                    "No uploaded artifact found and no server-local audio path "
                    "could be extracted from the user message."
                )
            transcription_result = transcribe_audio(audio_path=audio_path)

        transcript_text = str(transcription_result.get("text", "")).strip()
        if not transcript_text:
            raise ValueError("Transcription returned empty text.")

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(
                state_delta={
                    self.output_key: transcript_text,
                }
            ),
        )


transcription_agent = DeterministicTranscriptionAgent(
    name="transcription_step",
    description=(
        "Deterministically transcribes the uploaded or referenced audio into text."
    ),
)

summary_agent = _build_summary_agent()

root_agent = SequentialAgent(
    name="medisprache_pipeline",
    description=(
        "Deterministic two-step pipeline: direct transcription, then strict "
        "German JSON summarization."
    ),
    sub_agents=[
        transcription_agent,
        summary_agent,
    ],
)

app = App(
    name=APP_NAME,
    root_agent=root_agent,
    plugins=[
        SaveFilesAsArtifactsPlugin(),
    ],
)
