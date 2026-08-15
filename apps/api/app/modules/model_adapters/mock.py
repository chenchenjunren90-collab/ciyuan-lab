"""Fixed Mock / fallback adapter used when the model is unavailable."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse

_DEFAULT_REPLY = (
    "Mock 适配器：模型服务未配置或暂不可用，已降级为固定回复。"
    "配置 XFYUN_SPARK_API_KEY / XFYUN_SPARK_API_SECRET 后即可使用真实模型。"
)


class MockAdapter(ModelAdapter):
    """Deterministic adapter that always returns a fixed response.

    Keeps the core learning flow demonstrable end-to-end without any model
    credentials, and acts as the fallback when the real model is down.
    """

    def __init__(self, *, model: str = "mock", reply: str = _DEFAULT_REPLY) -> None:
        self._model = model
        self._reply = reply

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        del messages  # Mock 忽略输入，返回固定回复
        return ModelResponse(
            content=self._reply,
            provider="mock",
            model=self._model,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )
