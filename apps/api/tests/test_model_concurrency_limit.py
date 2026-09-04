from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest

from app.modules.model_adapters import (
    ChatMessage,
    ConcurrencyLimitedModelAdapter,
    ModelRateLimitError,
    ModelResponse,
)


class BlockingAdapter:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        assert messages
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.02)
        self.active -= 1
        return ModelResponse(content="ok", provider="test", model="test", usage={})


def test_shared_model_calls_respect_concurrency_limit() -> None:
    async def scenario() -> int:
        delegate = BlockingAdapter()
        adapter = ConcurrencyLimitedModelAdapter(
            delegate,
            max_concurrency=2,
            queue_timeout_seconds=1,
        )
        messages = [ChatMessage(role="user", content="test")]
        await asyncio.gather(*(adapter.complete(messages) for _ in range(6)))
        return delegate.max_active

    assert asyncio.run(scenario()) == 2


def test_model_queue_timeout_returns_a_rate_limit_error() -> None:
    async def scenario() -> None:
        delegate = BlockingAdapter()
        adapter = ConcurrencyLimitedModelAdapter(
            delegate,
            max_concurrency=1,
            queue_timeout_seconds=0.001,
        )
        messages = [ChatMessage(role="user", content="test")]
        first = asyncio.create_task(adapter.complete(messages))
        await asyncio.sleep(0)
        with pytest.raises(ModelRateLimitError, match="正忙"):
            await adapter.complete(messages)
        await first

    asyncio.run(scenario())
