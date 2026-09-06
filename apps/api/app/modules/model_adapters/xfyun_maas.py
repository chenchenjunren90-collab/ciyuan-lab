"""Xfyun MaaS OpenAI-compatible adapter for hosted foundation models."""

from __future__ import annotations

import httpx

from app.modules.model_adapters.xfyun import XfyunSparkAdapter


class XfyunMaaSAdapter(XfyunSparkAdapter):
    """Use the reviewed Spark HTTP transport against Xfyun MaaS.

    MaaS inference services use the same bearer-token, chat-completions request
    and response shape. The shared transport handles bounded retries, timeouts
    and safe errors while preserving MaaS identity in responses and diagnostics.
    """

    _provider_name = "xfyun-maas"
    _provider_label = "Xfyun MaaS"
    _config_prefix = "XFYUN_MAAS"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
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
