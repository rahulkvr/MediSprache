from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, Type

from pydantic import BaseModel


@dataclass(frozen=True)
class PromptExample:
    transcript_excerpt: str
    output_fragment: Mapping[str, Any]


@dataclass(frozen=True)
class PromptConfig:
    system_header: str
    task_lines: Sequence[str]
    field_guidance: Mapping[str, str] = field(default_factory=dict)
    long_context_lines: Sequence[str] = field(default_factory=tuple)
    output_rules: Sequence[str] = field(default_factory=tuple)
    consistency_checks: Sequence[str] = field(default_factory=tuple)
    examples: Sequence[PromptExample] = field(default_factory=tuple)


def _humanize_field_name(field_name: str) -> str:
    return field_name.replace("_", " ")


def _is_required_field(field_name: str, schema_dict: Mapping[str, Any]) -> bool:
    required = schema_dict.get("required") or []
    return field_name in required


def _render_field_guidance(
    schema_model: Type[BaseModel],
    guidance_overrides: Mapping[str, str],
) -> list[str]:
    schema_dict = schema_model.model_json_schema()
    properties = schema_dict.get("properties") or {}

    lines: list[str] = []
    for field_name in properties:
        description = guidance_overrides.get(field_name)
        if not description:
            schema_description = (properties.get(field_name) or {}).get("description")
            description = schema_description or _humanize_field_name(field_name)

        required_label = "required" if _is_required_field(field_name, schema_dict) else "optional"
        lines.append(f"- `{field_name}` ({required_label}): {description}")

    return lines


def _render_examples(examples: Sequence[PromptExample]) -> list[str]:
    if not examples:
        return []

    lines: list[str] = ["Examples:"]
    for idx, example in enumerate(examples, start=1):
        lines.append(f"Example {idx} input transcript excerpt:")
        lines.append(f'"{example.transcript_excerpt}"')
        lines.append("Example output JSON fragment:")
        lines.append(
            json.dumps(
                example.output_fragment,
                ensure_ascii=False,
                indent=2,
            )
        )
    return lines


def build_schema_instruction(
    *,
    schema_model: Type[BaseModel],
    config: PromptConfig,
    transcript_state_key: str,
) -> str:
    schema_json = json.dumps(
        schema_model.model_json_schema(),
        ensure_ascii=False,
        indent=2,
    )

    lines: list[str] = [config.system_header, "", "Transcript text (from previous step):"]
    lines.append("{" + transcript_state_key + "?}")

    lines.extend(["", "Task:"])
    lines.extend(config.task_lines)

    field_lines = _render_field_guidance(schema_model, config.field_guidance)
    if field_lines:
        lines.extend(["", "Field mapping guidance:"])
        lines.extend(field_lines)

    if config.long_context_lines:
        lines.extend(["", "Long-transcript handling:"])
        lines.extend(config.long_context_lines)

    if config.output_rules:
        lines.extend(["", "Output rules:"])
        lines.extend(config.output_rules)

    if config.consistency_checks:
        lines.extend(["", "Consistency check before final answer:"])
        lines.extend(config.consistency_checks)

    example_lines = _render_examples(config.examples)
    if example_lines:
        lines.extend([""])
        lines.extend(example_lines)

    lines.extend(["", "Required JSON schema:", schema_json])

    return "\n".join(lines).strip()
