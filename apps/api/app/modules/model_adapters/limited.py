"""Bound shared model capacity so concurrent learners cannot exhaust one MaaS service."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.modules.model_adapters.errors import ModelRateLimitError
from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse


class ConcurrencyLimitedModelAdapter:
    """Queue a bounded number of model calls and reject excessive wait safely."""

    def __init__(
        self,
        delegate: ModelAdapter,
        *,
        max_concurrency: int,
        queue_timeout_seconds: float,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        if queue_timeout_seconds <= 0:
            raise ValueError("queue_timeout_seconds must be positive")
        self._delegate = delegate
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._queue_timeout_seconds = queue_timeout_seconds

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self._queue_timeout_seconds,
            )
        except TimeoutError as error:
            raise ModelRateLimitError(
                "共享模型服务正忙，请稍后重试"
            ) from error
        try:
            return await self._delegate.complete(messages)
        finally:
            self._semaphore.release()
