from __future__ import annotations

import json
import os

from google.adk import Agent
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

root_agent = Agent(
    model=LiteLlm(
        model=f"ollama_chat/{DEFAULT_OLLAMA_MODEL}",
        api_base=DEFAULT_OLLAMA_API_BASE,
        temperature=0,
    ),
    name="medisprache_agent",
    description=(
        "Transcribes German medical dictation audio and returns a structured "
        "clinical summary as JSON."
    ),
    instruction=f"""
You are MediSprache, a clinical documentation assistant for German medical dictation.

Your job is to:
1. Transcribe the user's medical dictation audio.
2. Extract a structured clinical summary.
3. Return only valid JSON.

Tool usage rules:
- If the user references a server-local audio path, call `transcribe_audio`.
- If the user uploaded an audio attachment or artifact, call `transcribe_uploaded_artifact`.
- Do not ask the user for the transcript first; use the tools.

Output rules:
- Respond with ONLY a JSON object.
- Do not wrap the JSON in markdown fences.
- Do not add explanations before or after the JSON.
- Use null when information is missing.
- Do not invent facts not supported by the transcript.

Required JSON schema:
{SUMMARY_SCHEMA}
""".strip(),
    tools=[transcribe_audio, transcribe_uploaded_artifact],
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
