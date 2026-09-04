"""Xfyun MaaS OpenAI-compatible adapter for hosted foundation models."""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse
from app.modules.model_adapters.xfyun import XfyunSparkAdapter


class XfyunMaaSAdapter(ModelAdapter):
    """Use the reviewed Spark HTTP transport against Xfyun MaaS.

    MaaS inference services use the same bearer-token, chat-completions request
    and response shape. Composition keeps retries, error mapping and secret
    handling in one implementation while exposing the actual provider name.
    A configured ``lora_id`` is transmitted only for a reviewed MaaS LoRA route;
    the default general-model route remains header-free.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        lora_id: str = "",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        normalized_lora_id = lora_id.strip()
        self._delegate = XfyunSparkAdapter(
            base_url=base_url,
            api_password=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            extra_headers={"lora_id": normalized_lora_id} if normalized_lora_id else None,
            client=client,
        )

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        response = await self._delegate.complete(messages)
        return ModelResponse(
            content=response.content,
            provider="xfyun-maas",
            model=response.model,
            usage=response.usage,
        )
