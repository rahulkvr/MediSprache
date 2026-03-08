from __future__ import annotations

import json
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.models.llm_response import LlmResponse
from google.genai import types

_ALLOWED_TOOLS_STATE_KEY = "temp:allowed_tool_names"
_RESPONSE_TOOL_NAMES = {"response", "agent_response", "root"}


class OllamaToolCallBridgePlugin(BasePlugin):
    """Normalizes Ollama-style tool call payloads for ADK.

    Ollama models may emit tool invocations as plain JSON text instead of
    structured ``function_call`` parts. This plugin converts those payloads
    back into ADK-native function calls and formats tool responses into plain
    text for the next model turn.
    """

    def __init__(self, allowed_tool_names: set[str] | None = None) -> None:
        super().__init__(name="ollama_tool_call_bridge")
        self._allowed_tool_names = allowed_tool_names

    async def before_model_callback(self, *, callback_context, llm_request):
        allowed_names = set(self._allowed_tool_names or llm_request.tools_dict.keys())
        callback_context.state[_ALLOWED_TOOLS_STATE_KEY] = sorted(allowed_names)

        updated_contents: list[types.Content] = []
        changed = False

        for content in llm_request.contents:
            if not content.parts:
                updated_contents.append(content)
                continue

            updated_parts: list[types.Part] = []
            for part in content.parts:
                if part.function_response:
                    response = part.function_response.response or {}
                    response_text = json.dumps(
                        response,
                        ensure_ascii=False,
                        indent=2,
                    )
                    updated_parts.append(
                        types.Part(
                            text=(
                                f"Tool '{part.function_response.name}' returned:\n"
                                f"{response_text}"
                            )
                        )
                    )
                    changed = True
                else:
                    updated_parts.append(part)

            updated_contents.append(
                types.Content(role=content.role, parts=updated_parts)
            )

        if changed:
            llm_request.contents = updated_contents
        return None

    async def after_model_callback(self, *, callback_context, llm_response):
        if not llm_response.content or not llm_response.content.parts:
            return None

        allowed_names = set(self._allowed_tool_names or ())
        allowed_names.update(callback_context.state.get(_ALLOWED_TOOLS_STATE_KEY, []))

        updated_parts: list[types.Part] = []
        changed = False

        for part in llm_response.content.parts:
            converted = self._convert_text_part(part, allowed_names)
            if converted is None:
                updated_parts.append(part)
                continue

            updated_parts.extend(converted)
            changed = True

        if changed:
            llm_response.content = types.Content(
                role=llm_response.content.role,
                parts=updated_parts,
            )
            return llm_response
        return None

    def _convert_text_part(
        self,
        part: types.Part,
        allowed_names: set[str],
    ) -> list[types.Part] | None:
        if not part.text:
            return None

        text = part.text.strip()
        if not text.startswith("{"):
            return None

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        tool_name = payload.get("name")
        raw_args = payload.get("arguments", payload.get("parameters", {}))

        if tool_name in _RESPONSE_TOOL_NAMES:
            return [types.Part(text=self._extract_response_text(raw_args))]

        if tool_name not in allowed_names:
            return None

        args = self._normalize_args(raw_args)
        if args is None:
            return None

        return [types.Part(function_call=types.FunctionCall(name=tool_name, args=args))]

    def _extract_response_text(self, raw_args: Any) -> str:
        if isinstance(raw_args, str):
            return raw_args

        if isinstance(raw_args, list):
            return " ".join(str(item) for item in raw_args)

        if isinstance(raw_args, dict):
            for key in ("text", "response", "message", "content"):
                value = raw_args.get(key)
                if isinstance(value, str):
                    return value
                if isinstance(value, list):
                    return " ".join(str(item) for item in value)
            return json.dumps(raw_args, ensure_ascii=False)

        return str(raw_args)

    def _normalize_args(self, raw_args: Any) -> dict[str, Any] | None:
        if isinstance(raw_args, dict):
            return raw_args

        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
            except json.JSONDecodeError:
                return None
            return parsed if isinstance(parsed, dict) else None

        return None
