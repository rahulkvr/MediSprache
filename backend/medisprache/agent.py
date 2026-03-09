from __future__ import annotations

import json
import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.apps.app import App
from google.adk.models.lite_llm import LiteLlm
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin

from medisprache.plugins import OllamaToolCallBridgePlugin
from medisprache.schemas.clinical_summary import CompactClinicalSummary
from medisprache.tools.transcribe_audio import (
    transcribe_audio,
    transcribe_uploaded_artifact,
)

APP_NAME = "medisprache"
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
DEFAULT_OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
SUMMARY_SCHEMA = json.dumps(
    CompactClinicalSummary.model_json_schema(),
    ensure_ascii=False,
    indent=2,
)
TRANSCRIPT_STATE_KEY = "transcript_text"
SUMMARY_STATE_KEY = "clinical_summary"

transcription_agent = LlmAgent(
    model=LiteLlm(
        model=f"ollama_chat/{DEFAULT_OLLAMA_MODEL}",
        api_base=DEFAULT_OLLAMA_API_BASE,
        temperature=0,
    ),
    name="transcription_step",
    description="Transcribes German medical dictation audio into transcript text.",
    instruction="""
You are the transcription step in a deterministic clinical pipeline.

Your job is to transcribe the user's medical dictation audio.

Tool usage rules:
- If the user references a server-local audio path, call `transcribe_audio`.
- If the user uploaded an audio attachment or artifact, call `transcribe_uploaded_artifact`.
- Call exactly one transcription tool per request.

Output rules:
- After the tool returns, extract and return only the transcript text (`text` field).
- Do not return JSON.
- Do not add commentary or metadata.
""".strip(),
    tools=[transcribe_audio, transcribe_uploaded_artifact],
    output_key=TRANSCRIPT_STATE_KEY,
)

summary_agent = LlmAgent(
    model=LiteLlm(
        model=f"ollama_chat/{DEFAULT_OLLAMA_MODEL}",
        api_base=DEFAULT_OLLAMA_API_BASE,
        temperature=0,
    ),
    name="summary_step",
    description="Builds the final compact clinical summary JSON from transcript text.",
    instruction=f"""
You are the clinical summarization step in a deterministic pipeline.

Transcript text (from previous step):
{{transcript_text}}

Output rules:
- Respond with only a JSON object.
- Do not wrap JSON in markdown fences.
- Do not add explanations before or after JSON.
- All JSON field values must be written in German (Deutsch).
- Keep clinical terminology in German when possible.
- Use null when information is missing.
- Do not invent facts not supported by the transcript.

Required JSON schema:
{SUMMARY_SCHEMA}
""".strip(),
    output_schema=CompactClinicalSummary,
    output_key=SUMMARY_STATE_KEY,
)

root_agent = SequentialAgent(
    name="medisprache_pipeline",
    description=(
        "Deterministic two-step pipeline: transcribe audio first, then generate "
        "structured clinical summary JSON."
    ),
    sub_agents=[transcription_agent, summary_agent],
)

app = App(
    name=APP_NAME,
    root_agent=root_agent,
    plugins=[
        SaveFilesAsArtifactsPlugin(),
        OllamaToolCallBridgePlugin(
            allowed_tool_names={"transcribe_audio", "transcribe_uploaded_artifact"}
        ),
    ],
)
