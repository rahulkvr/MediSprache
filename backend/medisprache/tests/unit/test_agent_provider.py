from __future__ import annotations

import importlib

import pytest
from google.adk.models.google_llm import Gemini
from google.adk.models.lite_llm import LiteLlm


FIXED_OLLAMA_MODEL = "qwen2.5:1.5b"
FIXED_GEMINI_MODEL = "gemini-3-flash-preview"


def _load_agent_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    module = importlib.import_module("medisprache.agent")
    return importlib.reload(module)


def test_build_summary_model_for_ollama_uses_fixed_qwen(monkeypatch: pytest.MonkeyPatch):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_BASE", "http://ollama:11434")

    model = agent._build_summary_model("ollama")

    assert isinstance(model, LiteLlm)
    assert model.model == f"ollama_chat/{FIXED_OLLAMA_MODEL}"


def test_build_summary_model_for_gemini_uses_fixed_flash_model(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    model = agent._build_summary_model("gemini")

    assert isinstance(model, Gemini)
    assert model.model == FIXED_GEMINI_MODEL


def test_build_summary_agent_for_gemini_disables_output_schema(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    summary_agent = agent._build_summary_agent()

    assert summary_agent.output_schema is None
    assert summary_agent.output_key is None
    assert summary_agent.generate_content_config is not None
    assert summary_agent.generate_content_config.response_mime_type == "application/json"
    assert (
        summary_agent.generate_content_config.response_json_schema
        == agent.GEMINI_RESPONSE_JSON_SCHEMA
    )
    assert summary_agent.generate_content_config.thinking_config is not None
    assert (
        summary_agent.generate_content_config.thinking_config.thinking_level.value
        == "HIGH"
    )


def test_build_summary_agent_for_ollama_keeps_output_schema(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_BASE", "http://ollama:11434")

    summary_agent = agent._build_summary_agent()

    assert summary_agent.output_schema is agent.CompactClinicalSummary
    assert summary_agent.output_key == agent.SUMMARY_STATE_KEY


def test_build_summary_model_rejects_invalid_provider(monkeypatch: pytest.MonkeyPatch):
    agent = _load_agent_module(monkeypatch)

    with pytest.raises(ValueError, match="Unsupported provider"):
        agent._build_summary_model("invalid")


def test_missing_provider_raises_clear_error(monkeypatch: pytest.MonkeyPatch):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    with pytest.raises(ValueError, match="LLM_PROVIDER is required"):
        agent._resolve_llm_provider()


def test_invalid_provider_raises_clear_error(monkeypatch: pytest.MonkeyPatch):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        agent._resolve_llm_provider()


def test_gemini_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Gemini provider selected but no API key"):
        agent._build_summary_model("gemini")


@pytest.mark.parametrize(
    "env_var, bad_value",
    [
        ("OLLAMA_MODEL", "llama3.2:3b"),
        ("GEMINI_MODEL", "gemini-2.0-flash"),
    ],
)
def test_rejects_non_fixed_model_overrides(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    bad_value: str,
):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv(env_var, bad_value)

    with pytest.raises(ValueError, match=f"{env_var} is fixed in this app"):
        agent._validate_fixed_model_env_overrides()


def test_allows_fixed_model_override_values(monkeypatch: pytest.MonkeyPatch):
    agent = _load_agent_module(monkeypatch)
    monkeypatch.setenv("OLLAMA_MODEL", FIXED_OLLAMA_MODEL)
    monkeypatch.setenv("GEMINI_MODEL", FIXED_GEMINI_MODEL)

    agent._validate_fixed_model_env_overrides()