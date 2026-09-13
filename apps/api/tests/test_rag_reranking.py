import asyncio
from collections.abc import Sequence
from typing import cast

import pytest

from app.modules.model_adapters.errors import ModelTimeoutError
from app.modules.model_adapters.xfyun_maas_reranker import RankedDocument
from app.modules.rag.ports import KnowledgeRetrievalError, SearchHit
from app.modules.rag.reranking import RerankingKnowledgeRetriever


def hits() -> tuple[SearchHit, ...]:
    return tuple(
        SearchHit(
            source_id=f"SRC-PY-{index}",
            chunk_id=f"chunk-{index}",
            content=f"公开课程证据 {index}",
            score=0.8 - index * 0.1,
            metadata={"course_id": "python"},
        )
        for index in range(3)
    )


class Retriever:
    def __init__(self, result: Sequence[SearchHit]) -> None:
        self.result = result
        self.calls: list[tuple[str, str, int]] = []

    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        self.calls.append((query, course_id, top_k))
        return self.result[:top_k]


class Reranker:
    def __init__(self, result: tuple[RankedDocument, ...] = ()) -> None:
        self.result = result
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def rerank(self, *, query: str, documents: Sequence[str]) -> tuple[RankedDocument, ...]:
        self.calls.append((query, tuple(documents)))
        return self.result


def test_maas_rerank_only_reorders_supplied_course_evidence() -> None:
    original = hits()
    retriever = Retriever(original)
    reranker = Reranker((RankedDocument(index=2, score=0.99), RankedDocument(index=0, score=0.2)))
    wrapper = RerankingKnowledgeRetriever(retriever, reranker, candidate_limit=3)
    result = asyncio.run(wrapper.search("列表的特点", "python", 3))
    assert [hit.chunk_id for hit in result] == ["chunk-2", "chunk-0", "chunk-1"]
    assert retriever.calls == [("列表的特点", "python", 3)]
    assert reranker.calls == [("列表的特点", tuple(hit.content for hit in original))]
    for hit in result:
        source = next(item for item in original if item.chunk_id == hit.chunk_id)
        assert (hit.source_id, hit.content, hit.score) == (
            source.source_id,
            source.content,
            source.score,
        )
        assert hit.metadata["rerank_status"] == "completed"
    assert result[-1].metadata["rerank_scored"] is False


def test_rerank_timeout_preserves_retrieval_and_marks_degradation() -> None:
    class Unavailable(Reranker):
        async def rerank(
            self, *, query: str, documents: Sequence[str]
        ) -> tuple[RankedDocument, ...]:
            raise ModelTimeoutError("private provider diagnostic must not be exposed")

    original = hits()
    wrapper = RerankingKnowledgeRetriever(Retriever(original), Unavailable())
    result = asyncio.run(wrapper.search("query", "python", 2))
    assert [hit.chunk_id for hit in result] == ["chunk-0", "chunk-1"]
    assert all(hit.metadata["rerank_status"] == "degraded" for hit in result)
    assert all(hit.metadata["rerank_reason"] == "MODEL_TIMEOUT" for hit in result)
    assert "private" not in str(result)


@pytest.mark.parametrize(
    "ranks",
    [
        (),
        (RankedDocument(index=3, score=0.9),),
        (RankedDocument(index=0, score=float("nan")),),
        (RankedDocument(index=0, score=cast(float, "invalid")),),
        (RankedDocument(index=0, score=10**1000),),
        (cast(RankedDocument, {"index": 0, "score": 0.5}),),
        (RankedDocument(index=0, score=0.8), RankedDocument(index=0, score=0.9)),
    ],
)
def test_invalid_ranks_cannot_forge_citations(ranks: tuple[RankedDocument, ...]) -> None:
    wrapper = RerankingKnowledgeRetriever(Retriever(hits()), Reranker(ranks))
    result = asyncio.run(wrapper.search("query", "python", 2))
    assert [hit.chunk_id for hit in result] == ["chunk-0", "chunk-1"]
    assert all(hit.metadata["rerank_status"] == "degraded" for hit in result)


def test_empty_evidence_never_calls_maas() -> None:
    reranker = Reranker()
    wrapper = RerankingKnowledgeRetriever(Retriever(()), reranker)
    assert asyncio.run(wrapper.search("query", "python", 3)) == ()
    assert reranker.calls == []


@pytest.mark.parametrize(("query", "top_k"), [("", 3), (" \n ", 3), ("列表", 0)])
def test_empty_query_or_zero_limit_skips_retrieval_and_maas(query: str, top_k: int) -> None:
    retriever = Retriever(hits())
    reranker = Reranker()
    wrapper = RerankingKnowledgeRetriever(retriever, reranker)
    assert asyncio.run(wrapper.search(query, "python", top_k)) == ()
    assert retriever.calls == []
    assert reranker.calls == []


@pytest.mark.parametrize("ranks", [None, {"index": 0, "score": 0.5}, "bad response"])
def test_invalid_return_shape_degrades_without_losing_original_evidence(ranks: object) -> None:
    original = hits()
    reranker = Reranker(cast(tuple[RankedDocument, ...], ranks))
    wrapper = RerankingKnowledgeRetriever(Retriever(original), reranker)
    result = asyncio.run(wrapper.search("列表", "python", 2))
    assert [(hit.chunk_id, hit.content, hit.score) for hit in result] == [
        (hit.chunk_id, hit.content, hit.score) for hit in original[:2]
    ]
    assert all(hit.metadata["rerank_status"] == "degraded" for hit in result)


def test_candidate_limit_bounds_the_paid_request_without_dropping_unscored_results() -> None:
    original = hits()
    reranker = Reranker((RankedDocument(index=1, score=0.9),))
    wrapper = RerankingKnowledgeRetriever(Retriever(original), reranker, candidate_limit=2)
    result = asyncio.run(wrapper.search("列表", "python", 3))
    assert reranker.calls == [("列表", (original[0].content, original[1].content))]
    assert [hit.chunk_id for hit in result] == ["chunk-1", "chunk-0", "chunk-2"]
    assert len({hit.chunk_id for hit in result}) == 3


def test_database_failure_is_not_misreported_as_rerank_degradation() -> None:
    class Failed(Retriever):
        async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
            raise KnowledgeRetrievalError("database unavailable")

    reranker = Reranker()
    wrapper = RerankingKnowledgeRetriever(Failed(()), reranker)
    with pytest.raises(KnowledgeRetrievalError):
        asyncio.run(wrapper.search("query", "python", 3))
    assert reranker.calls == []


def test_oversized_evidence_is_not_silently_truncated_or_sent() -> None:
    reranker = Reranker()
    wrapper = RerankingKnowledgeRetriever(Retriever(hits()), reranker, max_document_chars=2)
    result = asyncio.run(wrapper.search("query", "python", 2))
    assert reranker.calls == []
    assert result[0].content == hits()[0].content
    assert result[0].metadata["rerank_reason"] == "candidate_too_long"
