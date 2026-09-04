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
    XfyunMaaSAdapter,
    build_model_adapter,
    build_python_tutor_model_adapter,
)


def test_maas_adapter_uses_openai_compatible_contract_without_lora_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == (
            "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
        )
        assert request.headers["Authorization"] == "Bearer test-maas-key"
        assert "lora_id" not in request.headers
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
        xfyun_maas_api_key=SecretStr("maas-key"),
        xfyun_spark_api_password=SecretStr("legacy-password"),
    )

    assert isinstance(build_model_adapter(settings), XfyunMaaSAdapter)


def test_python_tutor_route_sends_its_lora_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["lora_id"] == "resource-python-tutor-v1"
        body = json.loads(request.read().decode())
        assert body["model"] == "trained-python-tutor-model"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "model": "trained-python-tutor-model",
                "usage": {"total_tokens": 3},
            },
        )

    async def scenario() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = XfyunMaaSAdapter(
                base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
                api_key="test-maas-key",
                model="trained-python-tutor-model",
                lora_id="resource-python-tutor-v1",
                client=client,
            )
            response = await adapter.complete([ChatMessage(role="user", content="只回复ok")])
            return response.model

    assert asyncio.run(scenario()) == "trained-python-tutor-model"


def test_python_tutor_factory_reuses_general_model_until_lora_is_complete() -> None:
    general_settings = Settings(xfyun_maas_api_key=SecretStr("maas-key"))
    assert isinstance(build_python_tutor_model_adapter(general_settings), XfyunMaaSAdapter)

    trained_settings = Settings(
        xfyun_maas_api_key=SecretStr("maas-key"),
        xfyun_maas_python_tutor_enabled=True,
        xfyun_maas_python_tutor_model="trained-python-tutor-model",
        xfyun_maas_python_tutor_lora_id="resource-python-tutor-v1",
    )
    assert isinstance(build_python_tutor_model_adapter(trained_settings), XfyunMaaSAdapter)


def test_python_tutor_factory_rejects_partial_lora_configuration() -> None:
    settings = Settings(
        xfyun_maas_api_key=SecretStr("maas-key"),
        xfyun_maas_python_tutor_enabled=True,
        xfyun_maas_python_tutor_model="trained-python-tutor-model",
        xfyun_maas_python_tutor_lora_id="",
    )

    with pytest.raises(ModelConfigurationError, match="must be configured together"):
        build_python_tutor_model_adapter(settings)
