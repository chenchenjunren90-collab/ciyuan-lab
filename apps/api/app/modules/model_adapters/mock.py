"""Fixed Mock / fallback adapter used when the model is unavailable."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse

_DEFAULT_REPLY = (
    "Mock 适配器：模型服务未配置，已降级为固定回复。"
    "配置 XFYUN_MAAS_API_KEY 后即可使用讯飞MaaS真实模型。"
)


class MockAdapter(ModelAdapter):
    """Deterministic adapter that always returns a fixed response.

    Keeps the core learning flow demonstrable end-to-end when credentials are
    intentionally absent. Runtime failures from a configured real provider are
    surfaced as errors instead of being disguised as successful Mock replies.
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
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
