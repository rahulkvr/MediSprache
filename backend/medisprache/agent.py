from __future__ import annotations

import os
import re
from typing import AsyncGenerator

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.context import Context
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps.app import App
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.models.lite_llm import LiteLlm
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin

from medisprache.prompts import build_schema_instruction, get_prompt_profile
from medisprache.prompts.registry import COMPACT_CLINICAL_SUMMARY_PROMPT_ID
from medisprache.schemas.clinical_summary import CompactClinicalSummary
from medisprache.tools.transcribe_audio import transcribe_audio, transcribe_uploaded_artifact

APP_NAME = "medisprache"
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
DEFAULT_OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
TRANSCRIPT_STATE_KEY = "transcript_text"
SUMMARY_STATE_KEY = "clinical_summary"
SUMMARY_PROMPT_ID = os.getenv("SUMMARY_PROMPT_ID", COMPACT_CLINICAL_SUMMARY_PROMPT_ID)

SUMMARY_INSTRUCTION = build_schema_instruction(
    schema_model=CompactClinicalSummary,
    config=get_prompt_profile(SUMMARY_PROMPT_ID),
    transcript_state_key=TRANSCRIPT_STATE_KEY,
)


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

    quoted_match = re.search(
        r"""[\"']([^\"']+\.(?:mp3|wav|m4a|ogg|flac))[\"']""",
        combined_text,
        flags=re.IGNORECASE,
    )
    if quoted_match:
        return quoted_match.group(1)

    bare_match = re.search(
        r"""([A-Za-z]:[^\s\"']+\.(?:mp3|wav|m4a|ogg|flac)|/[^\s\"']+\.(?:mp3|wav|m4a|ogg|flac))""",
        combined_text,
        flags=re.IGNORECASE,
    )
    if bare_match:
        return bare_match.group(1).rstrip(".,)")

    return None


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

summary_agent = LlmAgent(
    model=LiteLlm(
        model=f"ollama_chat/{DEFAULT_OLLAMA_MODEL}",
        api_base=DEFAULT_OLLAMA_API_BASE,
        temperature=0,
    ),
    name="summary_step",
    description="Builds a compact clinical summary JSON from transcript text.",
    instruction=SUMMARY_INSTRUCTION,
    output_schema=CompactClinicalSummary,
    output_key=SUMMARY_STATE_KEY,
)

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
