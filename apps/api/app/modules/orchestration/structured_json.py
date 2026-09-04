"""Strict JSON-object parsing for model outputs.

Models occasionally wrap otherwise valid JSON in a Markdown code fence.  Some
reasoning-capable providers also prepend an empty ``<think></think>`` marker.
The orchestration layer accepts only those well-defined variations, but
deliberately rejects prose, non-empty reasoning, duplicate keys, non-finite
numbers and incomplete or mislabelled fences.  This keeps the parser useful
without turning it into a "find the first brace" extractor that could hide
additional model output.
"""

from __future__ import annotations

import json
import re
from typing import Any

_COMPLETE_JSON_FENCE = re.compile(
    r"\A```(?:json)?[ \t]*\r?\n(?P<body>[\s\S]*?)\r?\n```[ \t]*\Z",
    re.IGNORECASE,
)
_EMPTY_THINKING_PREFIX = re.compile(r"\A<think>[ \t\r\n]*</think>[ \t\r\n]*", re.IGNORECASE)


def parse_strict_json_object(content: str, *, max_chars: int = 12_000) -> dict[str, Any] | None:
    """Return one complete JSON object or ``None`` for any ambiguous shape."""

    if not isinstance(content, str):
        return None
    normalized = content.strip()
    if not normalized or len(normalized) > max_chars:
        return None

    # Qwen reasoning-mode responses may retain this empty marker even when the
    # requested answer is strict JSON.  Never discard non-empty reasoning or
    # arbitrary prose: those remain invalid structured output.
    normalized = _EMPTY_THINKING_PREFIX.sub("", normalized, count=1).strip()
    if not normalized:
        return None

    if normalized.startswith("```") or normalized.endswith("```"):
        match = _COMPLETE_JSON_FENCE.fullmatch(normalized)
        if match is None:
            return None
        normalized = match.group("body").strip()
        if not normalized:
            return None

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_non_finite(_: str) -> None:
        raise ValueError("non-finite JSON number")

    try:
        payload = json.loads(
            normalized,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None
