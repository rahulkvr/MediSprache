from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["agent", "app", "root_agent"]


def _load_agent_module() -> Any:
    return import_module(".agent", __name__)


def __getattr__(name: str) -> Any:
    if name == "agent":
        return _load_agent_module()
    if name in ("app", "root_agent"):
        return getattr(_load_agent_module(), name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
