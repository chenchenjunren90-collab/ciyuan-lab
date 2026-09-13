from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.model_adapters import (
    ChatMessage,
    DeepSeekAdapter,
    MockAdapter,
    ModelConfigurationError,
    ModelRateLimitError,
    ModelUpstreamError,
    build_model_adapter,
)


def test_deepseek_adapter_uses_openai_compatible_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-deepseek-key"
        body = json.loads(request.read().decode())
        assert body == {
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": "只回复ok"}],
            "stream": False,
        }
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "model": "deepseek-v4-flash",
                "usage": {"total_tokens": 3},
            },
        )

    async def scenario() -> tuple[str, str]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                base_url="https://api.deepseek.com",
                api_key="test-deepseek-key",
                model="deepseek-v4-flash",
                client=client,
            )
            response = await adapter.complete([ChatMessage(role="user", content="只回复ok")])
            return response.provider, response.content

    assert asyncio.run(scenario()) == ("deepseek", "ok")


def test_deepseek_structured_prompts_enable_native_json_mode() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read().decode())
        assert body["response_format"] == {"type": "json_object"}
        assert body["max_tokens"] == 2048
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"answer":"ok"}'}}],
                "model": "deepseek-v4-flash",
            },
        )

    async def scenario() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                base_url="https://api.deepseek.com",
                api_key="test-deepseek-key",
                model="deepseek-v4-flash",
                client=client,
            )
            response = await adapter.complete(
                [ChatMessage(role="system", content="只输出 JSON 对象")]
            )
            return response.content

    assert asyncio.run(scenario()) == '{"answer":"ok"}'


def test_factory_routes_to_deepseek_when_provider_is_selected() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        model_provider="deepseek",
        deepseek_api_key=SecretStr("deepseek-key"),
        xfyun_maas_api_key=SecretStr("maas-key"),
    )

    assert isinstance(build_model_adapter(settings), DeepSeekAdapter)


def test_factory_mock_fallback_for_unconfigured_deepseek_route() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        model_provider="deepseek",
        deepseek_api_key=SecretStr(""),
        xfyun_maas_mock_fallback=True,
        xfyun_spark_mock_fallback=True,
    )

    assert isinstance(build_model_adapter(settings), MockAdapter)


def test_factory_raises_for_deepseek_route_with_fallback_disabled() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        model_provider="deepseek",
        deepseek_api_key=SecretStr(""),
        xfyun_maas_mock_fallback=False,
        xfyun_spark_mock_fallback=False,
    )

    with pytest.raises(ModelConfigurationError, match="DEEPSEEK_API_KEY"):
        build_model_adapter(settings)


def test_deepseek_http_errors_keep_provider_identity_and_hide_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                base_url="https://api.deepseek.com",
                api_key="test-deepseek-key",
                model="deepseek-v4-flash",
                client=client,
            )
            await adapter.complete([ChatMessage(role="user", content="只回复ok")])

    with pytest.raises(ModelUpstreamError, match="DeepSeek") as caught:
        asyncio.run(scenario())
    assert "invalid api key" not in str(caught.value)


def test_deepseek_rate_limit_retries_then_raises() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                base_url="https://api.deepseek.com",
                api_key="test-deepseek-key",
                model="deepseek-v4-flash",
                max_retries=2,
                client=client,
            )
            await adapter.complete([ChatMessage(role="user", content="只回复ok")])

    with pytest.raises(ModelRateLimitError, match="DeepSeek"):
        asyncio.run(scenario())
    assert calls == 3


def test_deepseek_empty_assistant_content_recovers_on_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200, json={"code": 0, "choices": [{"message": {"content": ""}}]}
            )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "choices": [{"message": {"content": "ok"}}],
                "model": "deepseek-v4-flash",
            },
        )

    async def scenario() -> tuple[str, str]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                base_url="https://api.deepseek.com",
                api_key="test-deepseek-key",
                model="deepseek-v4-flash",
                max_retries=1,
                client=client,
            )
            response = await adapter.complete([ChatMessage(role="user", content="只回复ok")])
            return response.provider, response.content

    assert asyncio.run(scenario()) == ("deepseek", "ok")
    assert calls == 2


def test_deepseek_invalid_configuration_identifies_the_service() -> None:
    with pytest.raises(ModelConfigurationError, match="DEEPSEEK_MODEL"):
        DeepSeekAdapter(
            base_url="https://api.deepseek.com",
            api_key="test-deepseek-key",
            model=" ",
        )
