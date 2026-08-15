"""Tests for the model_adapters module (Issue AI-01)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.model_adapters import (
    ChatMessage,
    MockAdapter,
    ModelConfigurationError,
    ModelRateLimitError,
    ModelResponse,
    ModelTimeoutError,
    ModelUpstreamError,
    XfyunSparkAdapter,
    build_model_adapter,
)

USER_MESSAGE = ChatMessage(role="user", content="你好")


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)


def _adapter_with(
    client: httpx.AsyncClient,
    *,
    api_key: str = "test-key",
    api_secret: str = "test-secret",
    max_retries: int = 0,
) -> XfyunSparkAdapter:
    return XfyunSparkAdapter(
        base_url="https://spark-api-open.xf-yun.com",
        api_key=api_key,
        api_secret=api_secret,
        model="generalv3.5",
        max_retries=max_retries,
        client=client,
    )


def test_complete_success_returns_model_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key:test-secret"
        body = json.loads(request.read().decode())
        assert body["model"] == "generalv3.5"
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "model": "generalv3.5",
                "choices": [{"message": {"role": "assistant", "content": "你好，我是星火。"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
            },
        )

    async def scenario() -> ModelResponse:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client)
            return await adapter.complete([USER_MESSAGE])

    result = asyncio.run(scenario())

    assert isinstance(result, ModelResponse)
    assert result.content == "你好，我是星火。"
    assert result.provider == "xfyun"
    assert result.model == "generalv3.5"
    assert result.usage == {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8}


def test_complete_empty_messages_raises_configuration_error() -> None:
    async def scenario() -> None:
        async with _make_client(lambda _request: httpx.Response(200, json={})) as client:
            adapter = _adapter_with(client)
            await adapter.complete([])

    with pytest.raises(ModelConfigurationError, match="messages must not be empty"):
        asyncio.run(scenario())


def test_adapter_without_credentials_raises_configuration_error() -> None:
    with pytest.raises(ModelConfigurationError, match="not configured"):
        XfyunSparkAdapter(
            base_url="https://spark-api-open.xf-yun.com",
            api_key="",
            api_secret="",
            model="generalv3.5",
        )


def test_complete_timeout_raises_timeout_error_and_retries() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("read timeout")

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client, max_retries=1)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelTimeoutError, match="timed out"):
        asyncio.run(scenario())
    assert calls == 2


def test_complete_connection_error_raises_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.ConnectError("connection refused")

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelUpstreamError, match="connection failed"):
        asyncio.run(scenario())


def test_complete_rate_limit_raises_and_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client, max_retries=2)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelRateLimitError, match="429"):
        asyncio.run(scenario())
    assert calls == 1


def test_complete_5xx_retries_then_raises_upstream_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"error": "internal error"})

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client, max_retries=1)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelUpstreamError, match="HTTP 500"):
        asyncio.run(scenario())
    assert calls == 2


def test_complete_4xx_other_than_429_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": "unauthorized"})

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client, max_retries=2)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelUpstreamError, match="HTTP 401"):
        asyncio.run(scenario())
    assert calls == 1


def test_complete_5xx_then_success() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "temporarily unavailable"})
        return httpx.Response(
            200,
            json={
                "model": "generalv3.5",
                "choices": [{"message": {"role": "assistant", "content": "恢复成功"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            },
        )

    async def scenario() -> ModelResponse:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client, max_retries=1)
            return await adapter.complete([USER_MESSAGE])

    result = asyncio.run(scenario())

    assert result.content == "恢复成功"
    assert calls == 2


def test_complete_invalid_json_raises_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, text="not-json")

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelUpstreamError, match="invalid JSON"):
        asyncio.run(scenario())


def test_mock_adapter_returns_fixed_response() -> None:
    async def scenario() -> ModelResponse:
        adapter = MockAdapter(reply="固定回复")
        return await adapter.complete([USER_MESSAGE])

    result = asyncio.run(scenario())

    assert result.provider == "mock"
    assert result.model == "mock"
    assert result.content == "固定回复"
    assert result.usage == {"prompt_tokens": 0, "completion_tokens": 0}


def test_factory_builds_xfyun_adapter_when_configured() -> None:
    settings = Settings(
        xfyun_spark_api_key=SecretStr("key"),
        xfyun_spark_api_secret=SecretStr("secret"),
        xfyun_spark_model="generalv3.5",
        xfyun_spark_mock_fallback=True,
    )
    adapter = build_model_adapter(settings)
    assert isinstance(adapter, XfyunSparkAdapter)


def test_factory_returns_mock_adapter_when_unconfigured() -> None:
    settings = Settings(xfyun_spark_api_key=SecretStr(""), xfyun_spark_api_secret=SecretStr(""))
    adapter = build_model_adapter(settings)
    assert isinstance(adapter, MockAdapter)


def test_factory_raises_when_fallback_disabled() -> None:
    settings = Settings(
        xfyun_spark_api_key=SecretStr(""),
        xfyun_spark_api_secret=SecretStr(""),
        xfyun_spark_mock_fallback=False,
    )
    with pytest.raises(ModelConfigurationError, match="not configured"):
        build_model_adapter(settings)
