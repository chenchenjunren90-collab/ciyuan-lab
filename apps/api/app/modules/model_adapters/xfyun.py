"""Xfyun Spark adapter over the OpenAI-compatible HTTP endpoint."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.modules.model_adapters.errors import (
    ModelConfigurationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUpstreamError,
)
from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse

logger = logging.getLogger(__name__)

_CHAT_COMPLETIONS_PATH = "/chat/completions"
_RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})
_RATE_LIMIT_CODES = frozenset({10007, 11201, 11202, 11203})


class XfyunSparkAdapter(ModelAdapter):
    """Calls the Xfyun Spark OpenAI-compatible HTTP API.

    Authentication uses ``Authorization: Bearer {api_key}:{api_secret}``,
    the officially documented credential style for the OpenAI-compatible
    HTTP endpoint:

    The default endpoint and model follow the X2-Flash OpenAI-compatible
    protocol documented at https://www.xfyun.cn/doc/spark/X2-Flash.html:
    ``/agent/v1/chat/completions``, model ``spark-x``, and an ``AK:SK`` token.

    ``XFYUN_SPARK_APP_ID`` does NOT participate in this HTTP signature:
    the app_id + api_key + api_secret triple is only used to build the
    WebSocket handshake URLs of the older streaming protocol. The shared
    ``config.py`` exposes exactly the key/secret pair this adapter needs.

    Retry policy: only timeouts, request transport errors and HTTP 5xx statuses
    are retried, at most ``max_retries`` extra attempts. 4xx errors
    (including 429 rate limits) are surfaced immediately and never retried.
    Secrets are never written to logs.
    """

    _provider_name = "xfyun"
    _provider_label = "Xfyun Spark"
    _config_prefix = "XFYUN_SPARK"

    def __init__(
        self,
        *,
        base_url: str,
        api_password: str = "",
        api_key: str = "",
        api_secret: str = "",
        model: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise ModelConfigurationError(f"{self._config_prefix}_BASE_URL is not configured")
        parsed_url = urlsplit(normalized_base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ModelConfigurationError(f"{self._config_prefix}_BASE_URL must be an HTTP(S) URL")
        token = api_password.strip()
        normalized_api_key = api_key.strip()
        normalized_api_secret = api_secret.strip()
        if not token and normalized_api_key and normalized_api_secret:
            token = f"{normalized_api_key}:{normalized_api_secret}"
        if not token:
            raise ModelConfigurationError(f"{self._provider_label} credentials are not configured")

        if not model.strip():
            raise ModelConfigurationError(f"{self._config_prefix}_MODEL is not configured")
        if timeout_seconds <= 0:
            raise ModelConfigurationError("timeout_seconds must be greater than zero")
        if max_retries < 0:
            raise ModelConfigurationError("max_retries must not be negative")
        self._base_url = normalized_base_url
        self._token = token
        self._model = model.strip()
        self._timeout_seconds = timeout_seconds
        self._max_retries = int(max_retries)
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
            if attempt > 1:
                await asyncio.sleep(min(0.25 * 2 ** (attempt - 2), 2.0))
            try:
                response = await self._post(url, headers=headers, payload=payload)
            except httpx.TimeoutException:
                if attempt == attempts:
                    raise ModelTimeoutError(f"{self._provider_label} request timed out") from None
                logger.warning(
                    "%s request timed out (attempt %d/%d)",
                    self._provider_name,
                    attempt,
                    attempts,
                )
                continue
            except httpx.RequestError:
                if attempt == attempts:
                    raise ModelUpstreamError(
                        f"{self._provider_label} network request failed"
                    ) from None
                logger.warning(
                    "%s network request failed (attempt %d/%d)",
                    self._provider_name,
                    attempt,
                    attempts,
                )
                continue

            if response.status_code == 429:
                raise ModelRateLimitError(f"{self._provider_label} rate limited (HTTP 429)")

            if response.status_code in _RETRYABLE_STATUS_CODES:
                if attempt == attempts:
                    raise ModelUpstreamError(
                        f"{self._provider_label} returned HTTP {response.status_code}"
                    )
                logger.warning(
                    "%s returned HTTP %d (attempt %d/%d)",
                    self._provider_name,
                    response.status_code,
                    attempt,
                    attempts,
                )
                continue

            if response.status_code != 200:
                raise ModelUpstreamError(
                    f"{self._provider_label} returned HTTP {response.status_code}"
                )

            return self._parse_response(response)

        # Loop always returns or raises; kept for type narrowing.
        raise ModelUpstreamError(f"{self._provider_label} request failed")  # pragma: no cover

    async def _post(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        if self._client is not None:
            return await self._client.post(
                url, headers=headers, json=payload, timeout=self._timeout_seconds
            )
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await client.post(url, headers=headers, json=payload)

    def _build_payload(self, messages: Sequence[ChatMessage]) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
            "stream": False,
        }

    def _parse_response(self, response: httpx.Response) -> ModelResponse:
        try:
            data = response.json()
        except ValueError as exc:
            raise ModelUpstreamError(f"{self._provider_label} returned invalid JSON") from exc

        if not isinstance(data, dict):
            raise ModelUpstreamError(f"{self._provider_label} returned unexpected payload shape")

        response_code = data.get("code", 0)
        if isinstance(response_code, int) and not isinstance(response_code, bool):
            if response_code in _RATE_LIMIT_CODES:
                raise ModelRateLimitError(
                    f"{self._provider_label} rate limited (provider code {response_code})"
                )
            if response_code != 0:
                raise ModelUpstreamError(
                    f"{self._provider_label} rejected the request (provider code {response_code})"
                )
        elif response_code is not None:
            raise ModelUpstreamError(f"{self._provider_label} returned an invalid provider code")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelUpstreamError(f"{self._provider_label} response is missing choices")

        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        content = ""
        if isinstance(message, dict):
            content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ModelUpstreamError(
                f"{self._provider_label} response is missing assistant content"
            )

        usage: dict[str, int] = {}
        raw_usage = data.get("usage")
        if isinstance(raw_usage, dict):
            for key, value in raw_usage.items():
                if isinstance(value, int) and not isinstance(value, bool):
                    usage[key] = value

        model_name = data.get("model")
        return ModelResponse(
            content=content,
            provider=self._provider_name,
            model=model_name if isinstance(model_name, str) and model_name else self._model,
            usage=usage,
        )
