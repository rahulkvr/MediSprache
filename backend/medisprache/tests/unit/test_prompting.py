from __future__ import annotations

import pytest

from medisprache.prompts import build_schema_instruction, get_prompt_profile
from medisprache.prompts.registry import COMPACT_CLINICAL_SUMMARY_PROMPT_ID
from medisprache.schemas.clinical_summary import CompactClinicalSummary


def test_prompt_registry_returns_compact_summary_profile():
    profile = get_prompt_profile(COMPACT_CLINICAL_SUMMARY_PROMPT_ID)
    assert profile.system_header
    assert profile.task_lines


def test_prompt_registry_unknown_profile_raises():
    with pytest.raises(KeyError):
        get_prompt_profile("unknown.schema")


def test_build_schema_instruction_includes_schema_and_fields():
    profile = get_prompt_profile(COMPACT_CLINICAL_SUMMARY_PROMPT_ID)
    instruction = build_schema_instruction(
        schema_model=CompactClinicalSummary,
        config=profile,
        transcript_state_key="transcript_text",
    )

    assert "{transcript_text?}" in instruction
    assert "Required JSON schema:" in instruction
    assert "`patient_complaint` (optional):" in instruction
    assert "`findings` (optional):" in instruction
    assert "Output rules:" in instruction
