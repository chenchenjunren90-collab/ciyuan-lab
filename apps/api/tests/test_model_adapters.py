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
        base_url="https://spark-api-open.xf-yun.com/agent/v1",
        api_key=api_key,
        api_secret=api_secret,
        model="spark-x",
        max_retries=max_retries,
        client=client,
    )


def test_complete_success_returns_model_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == ("https://spark-api-open.xf-yun.com/agent/v1/chat/completions")
        assert request.headers["Authorization"] == "Bearer test-key:test-secret"
        body = json.loads(request.read().decode())
        assert body["model"] == "spark-x"
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "model": "spark-x",
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
    assert result.model == "spark-x"
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
            base_url="https://spark-api-open.xf-yun.com/agent/v1",
            api_key="",
            api_secret="",
            model="spark-x",
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

    with pytest.raises(ModelUpstreamError, match="network request failed"):
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
                "code": 0,
                "model": "spark-x",
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


@pytest.mark.parametrize("provider_code", [10007, 11201, 11202, 11203])
def test_complete_provider_rate_limit_code_is_mapped(provider_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"code": provider_code, "message": "limited"})

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelRateLimitError, match=str(provider_code)):
        asyncio.run(scenario())


def test_complete_provider_error_code_is_mapped_without_exposing_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"code": 11200, "message": "secret upstream diagnostic"},
        )

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelUpstreamError, match="provider code 11200") as exc_info:
        asyncio.run(scenario())
    assert "secret upstream diagnostic" not in str(exc_info.value)


def test_complete_other_request_error_retries_then_raises() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ProtocolError("broken response", request=request)

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client, max_retries=1)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelUpstreamError, match="network request failed"):
        asyncio.run(scenario())
    assert calls == 2


def test_complete_empty_content_raises_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"code": 0, "choices": [{"message": {"content": ""}}]},
        )

    async def scenario() -> None:
        async with _make_client(handler) as client:
            adapter = _adapter_with(client)
            await adapter.complete([USER_MESSAGE])

    with pytest.raises(ModelUpstreamError, match="assistant content"):
        asyncio.run(scenario())


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"base_url": "not-a-url"}, "HTTP\\(S\\) URL"),
        ({"model": " "}, "MODEL"),
        ({"timeout_seconds": 0.0}, "greater than zero"),
        ({"max_retries": -1}, "must not be negative"),
    ],
)
def test_adapter_rejects_invalid_configuration(
    overrides: dict[str, object], expected_message: str
) -> None:
    arguments: dict[str, object] = {
        "base_url": "https://spark-api-open.xf-yun.com/agent/v1",
        "api_key": "key",
        "api_secret": "secret",
        "model": "spark-x",
    }
    arguments.update(overrides)
    with pytest.raises(ModelConfigurationError, match=expected_message):
        XfyunSparkAdapter(**arguments)  # type: ignore[arg-type]


def test_mock_adapter_returns_fixed_response() -> None:
    async def scenario() -> ModelResponse:
        adapter = MockAdapter(reply="固定回复")
        return await adapter.complete([USER_MESSAGE])

    result = asyncio.run(scenario())

    assert result.provider == "mock"
    assert result.model == "mock"
    assert result.content == "固定回复"
    assert result.usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def test_factory_builds_xfyun_adapter_when_configured() -> None:
    settings = Settings(
        xfyun_maas_api_key=SecretStr(""),
        xfyun_spark_api_key=SecretStr("key"),
        xfyun_spark_api_secret=SecretStr("secret"),
        xfyun_spark_model="spark-x",
        xfyun_spark_mock_fallback=True,
    )
    adapter = build_model_adapter(settings)
    assert isinstance(adapter, XfyunSparkAdapter)


def test_http_api_password_is_supported_without_key_secret_pair() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer password-only"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "choices": [{"message": {"content": "ok"}}],
            },
        )

    async def scenario() -> ModelResponse:
        async with _make_client(handler) as client:
            adapter = XfyunSparkAdapter(
                base_url="https://spark-api-open.xf-yun.com/agent/v1",
                api_password="password-only",
                model="spark-x",
                client=client,
            )
            return await adapter.complete([USER_MESSAGE])

    assert asyncio.run(scenario()).content == "ok"


def test_factory_prefers_http_api_password() -> None:
    settings = Settings(
        xfyun_maas_api_key=SecretStr(""),
        xfyun_spark_api_password=SecretStr("password-only"),
        xfyun_spark_api_key=SecretStr(""),
        xfyun_spark_api_secret=SecretStr(""),
    )

    assert isinstance(build_model_adapter(settings), XfyunSparkAdapter)


def test_factory_returns_mock_adapter_when_unconfigured() -> None:
    settings = Settings(
        xfyun_maas_api_key=SecretStr(""),
        xfyun_spark_api_key=SecretStr(""),
        xfyun_spark_api_secret=SecretStr(""),
    )
    adapter = build_model_adapter(settings)
    assert isinstance(adapter, MockAdapter)


def test_factory_raises_when_fallback_disabled() -> None:
    settings = Settings(
        xfyun_maas_api_key=SecretStr(""),
        xfyun_spark_api_key=SecretStr(""),
        xfyun_spark_api_secret=SecretStr(""),
        xfyun_spark_mock_fallback=False,
    )
    with pytest.raises(ModelConfigurationError, match="not configured"):
        build_model_adapter(settings)
