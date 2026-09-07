"""DeepSeek official OpenAI-compatible adapter for the course tutor and supervisor."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from app.modules.model_adapters.ports import ChatMessage
from app.modules.model_adapters.xfyun import XfyunSparkAdapter


class DeepSeekAdapter(XfyunSparkAdapter):
    """Use the reviewed OpenAI-compatible HTTP transport against api.deepseek.com.

    The official DeepSeek API speaks the same bearer-token, chat-completions
    contract. The shared transport keeps bounded retries, timeouts and safe
    error mapping while preserving the DeepSeek identity in responses and
    diagnostics. Structured classroom prompts enable the provider's native
    JSON-output mode, reducing format-repair calls and evidence fallbacks.
    """

    _provider_name = "deepseek"
    _provider_label = "DeepSeek"
    _config_prefix = "DEEPSEEK"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 45.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_password=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            client=client,
        )

    def _build_payload(self, messages: Sequence[ChatMessage]) -> dict[str, Any]:
        payload = super()._build_payload(messages)
        if any("json" in message.content.casefold() for message in messages):
            payload["response_format"] = {"type": "json_object"}
            payload["max_tokens"] = 2048
        return payload
