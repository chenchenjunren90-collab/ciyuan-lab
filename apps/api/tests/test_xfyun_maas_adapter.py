from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.model_adapters import (
    ChatMessage,
    ModelConfigurationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUpstreamError,
    XfyunMaaSAdapter,
    build_model_adapter,
)


def test_maas_adapter_uses_openai_compatible_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == ("https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions")
        assert request.headers["Authorization"] == "Bearer test-maas-key"
        body = json.loads(request.read().decode())
        assert body == {
            "model": "xopdeepseekv4flash0731",
            "messages": [{"role": "user", "content": "只回复ok"}],
            "stream": False,
        }
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "model": "xopdeepseekv4flash0731",
                "usage": {"total_tokens": 3},
            },
        )

    async def scenario() -> tuple[str, str]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = XfyunMaaSAdapter(
                base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
                api_key="test-maas-key",
                model="xopdeepseekv4flash0731",
                client=client,
            )
            response = await adapter.complete([ChatMessage(role="user", content="只回复ok")])
            return response.provider, response.content

    assert asyncio.run(scenario()) == ("xfyun-maas", "ok")


def test_factory_prefers_maas_over_legacy_spark() -> None:
    settings = Settings(
        _env_file=None,
        xfyun_maas_api_key=SecretStr("maas-key"),
        xfyun_spark_api_password=SecretStr("legacy-password"),
    )

    assert isinstance(build_model_adapter(settings), XfyunMaaSAdapter)


def test_maas_adapter_honors_timeout_with_an_injected_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.extensions["timeout"] == {
            "connect": 7.0,
            "read": 7.0,
            "write": 7.0,
            "pool": 7.0,
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    async def scenario() -> str:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=None
        ) as client:
            adapter = XfyunMaaSAdapter(
                base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
                api_key="test-maas-key",
                model="hosted-model",
                timeout_seconds=7.0,
                client=client,
            )
            response = await adapter.complete([ChatMessage(role="user", content="只回复ok")])
            return response.content

    assert asyncio.run(scenario()) == "ok"


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, ModelUpstreamError), (429, ModelRateLimitError)],
)
def test_maas_client_errors_are_not_retried_or_exposed(
    status: int, error_type: type[Exception]
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, json={"error": "private upstream details"})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = XfyunMaaSAdapter(
                base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
                api_key="test-maas-key",
                model="hosted-model",
                max_retries=2,
                client=client,
            )
            await adapter.complete([ChatMessage(role="user", content="只回复ok")])

    with pytest.raises(error_type, match="Xfyun MaaS") as caught:
        asyncio.run(scenario())
    assert calls == 1
    assert "private upstream details" not in str(caught.value)


def test_maas_overload_retries_with_backoff_and_keeps_provider_identity(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    calls = 0
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.modules.model_adapters.xfyun.asyncio.sleep", record_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "private upstream details"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok", "reasoning_content": "private"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            },
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = XfyunMaaSAdapter(
                base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
                api_key="test-maas-key",
                model="hosted-model",
                max_retries=1,
                client=client,
            )
            result = await adapter.complete([ChatMessage(role="user", content="只回复ok")])
            assert result.provider == "xfyun-maas"
            assert result.content == "ok"
            assert result.usage["total_tokens"] == 4

    asyncio.run(scenario())
    assert calls == 2
    assert delays == [0.25]
    assert "xfyun-maas" in caplog.text
    assert "private" not in caplog.text
    assert "test-maas-key" not in caplog.text


def test_maas_timeout_uses_its_own_error_identity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private upstream details")

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = XfyunMaaSAdapter(
                base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
                api_key="test-maas-key",
                model="hosted-model",
                max_retries=0,
                client=client,
            )
            await adapter.complete([ChatMessage(role="user", content="只回复ok")])

    with pytest.raises(ModelTimeoutError, match="Xfyun MaaS request timed out"):
        asyncio.run(scenario())


def test_maas_invalid_configuration_identifies_the_actual_service() -> None:
    with pytest.raises(ModelConfigurationError, match="XFYUN_MAAS_MODEL"):
        XfyunMaaSAdapter(
            base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
            api_key="test-maas-key",
            model=" ",
        )


def test_maas_rejects_whitespace_only_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": " \n "}}]})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = XfyunMaaSAdapter(
                base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
                api_key="test-maas-key",
                model="hosted-model",
                client=client,
            )
            await adapter.complete([ChatMessage(role="user", content="只回复ok")])

    with pytest.raises(ModelUpstreamError, match="Xfyun MaaS.*assistant content"):
        asyncio.run(scenario())
