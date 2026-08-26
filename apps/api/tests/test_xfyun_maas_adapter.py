from __future__ import annotations

import asyncio
import json

import httpx
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.model_adapters import ChatMessage, XfyunMaaSAdapter, build_model_adapter


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
