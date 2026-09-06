"""Verify the MaaS rerank wire contract without calling a paid service."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.model_adapters import (
    ModelConfigurationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUpstreamError,
    RankedDocument,
    XfyunMaaSReranker,
    build_reranker,
)


async def _call(
    handler: Callable[[httpx.Request], httpx.Response], *, max_retries: int = 0
) -> tuple[RankedDocument, ...]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=None) as client:
        adapter = XfyunMaaSReranker(
            base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
            api_key="test-key",
            model="published-rerank-model",
            max_retries=max_retries,
            timeout_seconds=7,
            client=client,
        )
        return await adapter.rerank(query="列表筛选", documents=["for 遍历", "if 筛选"])


def test_rerank_uses_official_contract_and_sorts_unsorted_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://maas-api.cn-huabei-1.xf-yun.com/v2/rerank"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.extensions["timeout"]["read"] == 7
        assert json.loads(request.content) == {
            "model": "published-rerank-model",
            "query": "列表筛选",
            "documents": ["for 遍历", "if 筛选"],
        }
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 0, "relevance_score": 0.1, "document": "untrusted replacement"},
                    {"index": 1, "relevance_score": 0.9},
                ]
            },
        )

    assert asyncio.run(_call(handler)) == (RankedDocument(1, 0.9), RankedDocument(0, 0.1))


@pytest.mark.parametrize(
    "results",
    [
        [],
        [{"index": 2, "relevance_score": 0.5}],
        [{"index": -1, "relevance_score": 0.5}],
        [{"index": True, "relevance_score": 0.5}],
        [{"index": "0", "relevance_score": 0.5}],
        [{"index": 0, "relevance_score": 0.5}, {"index": 0, "relevance_score": 0.6}],
        [{"index": 0, "relevance_score": float("nan")}],
        [{"index": 0, "relevance_score": float("inf")}],
        [{"index": 0, "relevance_score": 10**1000}],
        [{"index": 0, "relevance_score": True}],
        [{"index": 0, "relevance_score": "0.5"}],
        [{"index": 0}],
        ["invalid"],
    ],
)
def test_invalid_ranks_cannot_enter_the_evidence_pool(results: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps({"results": results}))

    with pytest.raises(ModelUpstreamError, match="invalid"):
        asyncio.run(_call(handler))


def test_provider_can_return_a_valid_subset_without_new_documents() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [{"index": 1, "relevance_score": 0.8}]})

    assert asyncio.run(_call(handler)) == (RankedDocument(1, 0.8),)


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, ModelUpstreamError),
        (429, ModelRateLimitError),
    ],
)
def test_client_errors_are_not_retried(status: int, error_type: type[Exception]) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, json={"error": "private upstream detail"})

    with pytest.raises(error_type) as caught:
        asyncio.run(_call(handler, max_retries=2))
    assert calls == 1
    assert "private" not in str(caught.value)


def test_overload_retries_with_a_bounded_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    delays: list[float] = []

    async def record_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(
        "app.modules.model_adapters.xfyun_maas_reranker.asyncio.sleep", record_sleep
    )

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.2}]})

    assert asyncio.run(_call(handler, max_retries=1)) == (RankedDocument(0, 0.2),)
    assert calls == 2
    assert delays == [0.25]


def test_timeout_is_mapped_without_revealing_upstream_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private upstream details")

    with pytest.raises(ModelTimeoutError, match="MaaS reranker request timed out"):
        asyncio.run(_call(handler))


@pytest.mark.parametrize("body", ["not-json", "[]", '{"results": null}'])
def test_invalid_response_body_is_rejected(body: str) -> None:
    with pytest.raises(ModelUpstreamError, match="invalid"):
        asyncio.run(_call(lambda request: httpx.Response(200, text=body)))


def test_candidate_limit_is_enforced_before_any_network_request() -> None:
    adapter = XfyunMaaSReranker(
        base_url="https://maas-api.cn-huabei-1.xf-yun.com/v2",
        api_key="test-key",
        model="published-rerank-model",
        candidate_limit=1,
    )
    with pytest.raises(ModelConfigurationError, match="bounded candidates"):
        asyncio.run(adapter.rerank(query="列表", documents=["first", "second"]))


def test_reranking_is_disabled_unless_explicitly_configured() -> None:
    assert build_reranker(Settings(_env_file=None)) is None
    with pytest.raises(ModelConfigurationError, match="key and model"):
        build_reranker(Settings(_env_file=None, xfyun_maas_reranker_enabled=True))


def test_factory_can_use_the_existing_maas_key_or_a_dedicated_key() -> None:
    for dedicated_key in ("", "dedicated-key"):
        settings = Settings(
            _env_file=None,
            xfyun_maas_api_key=SecretStr("main-key"),
            xfyun_maas_reranker_api_key=SecretStr(dedicated_key),
            xfyun_maas_reranker_enabled=True,
            xfyun_maas_reranker_model="published-rerank-model",
        )
        assert isinstance(build_reranker(settings), XfyunMaaSReranker)
