"""Xfyun Spark adapter over the OpenAI-compatible HTTP endpoint."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import httpx

from app.modules.model_adapters.errors import (
    ModelConfigurationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUpstreamError,
)
from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse

logger = logging.getLogger(__name__)

_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
_RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})


class XfyunSparkAdapter(ModelAdapter):
    """Calls the Xfyun Spark OpenAI-compatible HTTP API.

    Authentication uses ``Authorization: Bearer {api_key}:{api_secret}``,
    the officially documented credential style for the OpenAI-compatible
    HTTP endpoint:

    * Agent04-API 接入文档: https://www.xfyun.cn/doc/spark/Agent04-API%E6%8E%A5%E5%85%A5.html
      ("鉴权码组成：``Bearer {API_KEY}:{API_SECRET}``")
    * X2-Flash 文档: https://www.xfyun.cn/doc/spark/X2-Flash.html
      (OpenAI SDK 兼容, ``api_key="AK:SK"`` 即 key/secret 拼接)

    ``XFYUN_SPARK_APP_ID`` does NOT participate in this HTTP signature:
    the app_id + api_key + api_secret triple is only used to build the
    WebSocket handshake URLs of the older streaming protocol. The shared
    ``config.py`` exposes exactly the key/secret pair this adapter needs.

    Retry policy: only timeouts, connection errors and HTTP 5xx statuses
    are retried, at most ``max_retries`` extra attempts. 4xx errors
    (including 429 rate limits) are surfaced immediately and never retried.
    Secrets are never written to logs.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        api_secret: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ModelConfigurationError("XFYUN_SPARK_BASE_URL is not configured")
        if not api_key.strip() or not api_secret.strip():
            raise ModelConfigurationError(
                "XFYUN_SPARK_API_KEY / XFYUN_SPARK_API_SECRET is not configured"
            )

        self._base_url = base_url.rstrip("/")
        self._token = f"{api_key}:{api_secret}"
        self._model = model
        self._timeout_seconds = max(0.1, timeout_seconds)
        self._max_retries = max(0, int(max_retries))
        self._client = client

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        if not messages:
            raise ModelConfigurationError("messages must not be empty")

        payload = self._build_payload(messages)
        url = f"{self._base_url}{_CHAT_COMPLETIONS_PATH}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        attempts = self._max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self._post(url, headers=headers, payload=payload)
            except httpx.TimeoutException:
                if attempt == attempts:
                    raise ModelTimeoutError("Xfyun Spark request timed out") from None
                logger.warning(
                    "xfyun spark request timed out (attempt %d/%d)", attempt, attempts
                )
                continue
            except httpx.ConnectError:
                if attempt == attempts:
                    raise ModelUpstreamError("Xfyun Spark connection failed") from None
                logger.warning(
                    "xfyun spark connection failed (attempt %d/%d)", attempt, attempts
                )
                continue

            if response.status_code == 429:
                raise ModelRateLimitError("Xfyun Spark rate limited (HTTP 429)")

            if response.status_code in _RETRYABLE_STATUS_CODES:
                if attempt == attempts:
                    raise ModelUpstreamError(
                        f"Xfyun Spark returned HTTP {response.status_code}"
                    )
                logger.warning(
                    "xfyun spark returned HTTP %d (attempt %d/%d)",
                    response.status_code,
                    attempt,
                    attempts,
                )
                continue

            if response.status_code != 200:
                raise ModelUpstreamError(
                    f"Xfyun Spark returned HTTP {response.status_code}"
                )

            return self._parse_response(response)

        # Loop always returns or raises; kept for type narrowing.
        raise ModelUpstreamError("Xfyun Spark request failed")  # pragma: no cover

    async def _post(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        if self._client is not None:
            return await self._client.post(url, headers=headers, json=payload)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await client.post(url, headers=headers, json=payload)

    def _build_payload(self, messages: Sequence[ChatMessage]) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "stream": False,
        }

    def _parse_response(self, response: httpx.Response) -> ModelResponse:
        try:
            data = response.json()
        except ValueError as exc:
            raise ModelUpstreamError("Xfyun Spark returned invalid JSON") from exc

        if not isinstance(data, dict):
            raise ModelUpstreamError("Xfyun Spark returned unexpected payload shape")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelUpstreamError("Xfyun Spark response is missing choices")

        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        content = ""
        if isinstance(message, dict):
            content = message.get("content", "")
        if not isinstance(content, str):
            content = str(content)

        usage: dict[str, int] = {}
        raw_usage = data.get("usage")
        if isinstance(raw_usage, dict):
            for key, value in raw_usage.items():
                if isinstance(value, int):
                    usage[key] = value

        model_name = data.get("model")
        return ModelResponse(
            content=content,
            provider="xfyun",
            model=model_name if isinstance(model_name, str) and model_name else self._model,
            usage=usage,
        )
