"""MaaS relevance scoring restricted to the caller's retrieved candidates."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from app.modules.model_adapters.errors import (
    ModelConfigurationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUpstreamError,
)


@dataclass(frozen=True, slots=True)
class RankedDocument:
    index: int
    score: float


class DocumentReranker(Protocol):
    async def rerank(
        self, *, query: str, documents: Sequence[str]
    ) -> tuple[RankedDocument, ...]: ...


class XfyunMaaSReranker:
    """Use the documented /rerank API without admitting new source documents."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        candidate_limit: int = 12,
        timeout_seconds: float = 8.0,
        max_retries: int = 1,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        normalized_url = base_url.strip().rstrip("/")
        parsed = urlsplit(normalized_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise ModelConfigurationError("MaaS reranker base URL must be an HTTP(S) root URL")
        if not api_key.strip() or not model.strip():
            raise ModelConfigurationError("MaaS reranker API key and model must be configured")
        if (
            isinstance(candidate_limit, bool)
            or not isinstance(candidate_limit, int)
            or not 1 <= candidate_limit <= 20
        ):
            raise ModelConfigurationError("MaaS reranker candidate limit must be between 1 and 20")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ModelConfigurationError("MaaS reranker timeout must be finite and positive")
        if (
            isinstance(max_retries, bool)
            or not isinstance(max_retries, int)
            or not 0 <= max_retries <= 5
        ):
            raise ModelConfigurationError("MaaS reranker retries must be an integer from 0 to 5")
        self._url = f"{normalized_url}/rerank"
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._candidate_limit = candidate_limit
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._client = client

    async def rerank(self, *, query: str, documents: Sequence[str]) -> tuple[RankedDocument, ...]:
        candidates = tuple(documents)
        if not query.strip() or not 1 <= len(candidates) <= self._candidate_limit:
            raise ModelConfigurationError("MaaS reranker requires a query and bounded candidates")
        if any(not isinstance(document, str) or not document.strip() for document in candidates):
            raise ModelConfigurationError("MaaS reranker candidates must be nonempty text")
        if self._client is not None:
            return await self._request(self._client, query, candidates)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._request(client, query, candidates)

    async def _request(
        self, client: httpx.AsyncClient, query: str, candidates: tuple[str, ...]
    ) -> tuple[RankedDocument, ...]:
        for attempt in range(self._max_retries + 1):
            if attempt:
                await asyncio.sleep(min(0.25 * 2 ** (attempt - 1), 2.0))
            try:
                response = await client.post(
                    self._url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": self._model, "query": query, "documents": list(candidates)},
                    timeout=self._timeout,
                )
            except httpx.TimeoutException:
                if attempt == self._max_retries:
                    raise ModelTimeoutError("Xfyun MaaS reranker request timed out") from None
                continue
            except httpx.RequestError:
                if attempt == self._max_retries:
                    raise ModelUpstreamError("Xfyun MaaS reranker network request failed") from None
                continue
            if response.status_code == 429:
                raise ModelRateLimitError("Xfyun MaaS reranker rate limited (HTTP 429)")
            if response.status_code in {500, 502, 503, 504} and attempt < self._max_retries:
                continue
            if response.status_code != 200:
                raise ModelUpstreamError(
                    f"Xfyun MaaS reranker returned HTTP {response.status_code}"
                )
            return self._parse_response(response, len(candidates))
        raise ModelUpstreamError("Xfyun MaaS reranker request failed")  # pragma: no cover

    @staticmethod
    def _parse_response(response: httpx.Response, count: int) -> tuple[RankedDocument, ...]:
        try:
            payload = response.json()
        except ValueError:
            raise ModelUpstreamError("Xfyun MaaS reranker returned invalid JSON") from None
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list) or not 1 <= len(results) <= count:
            raise ModelUpstreamError("Xfyun MaaS reranker returned invalid results")
        ranked: list[RankedDocument] = []
        seen: set[int] = set()
        for result in results:
            if not isinstance(result, dict):
                raise ModelUpstreamError("Xfyun MaaS reranker returned an invalid result")
            index = result.get("index")
            score = result.get("relevance_score")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < count
                or index in seen
            ):
                raise ModelUpstreamError("Xfyun MaaS reranker returned an invalid candidate index")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ModelUpstreamError("Xfyun MaaS reranker returned an invalid relevance score")
            try:
                normalized_score = float(score)
            except OverflowError:
                raise ModelUpstreamError(
                    "Xfyun MaaS reranker returned an invalid relevance score"
                ) from None
            if not math.isfinite(normalized_score):
                raise ModelUpstreamError("Xfyun MaaS reranker returned an invalid relevance score")
            seen.add(index)
            ranked.append(RankedDocument(index=index, score=normalized_score))
        return tuple(sorted(ranked, key=lambda document: (-document.score, document.index)))
