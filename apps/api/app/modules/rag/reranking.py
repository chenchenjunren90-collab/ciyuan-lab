"""Rerank existing course evidence through MaaS without creating new citations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace

from app.modules.model_adapters.errors import ModelError, ModelUpstreamError
from app.modules.model_adapters.xfyun_maas_reranker import DocumentReranker, RankedDocument
from app.modules.rag.ports import KnowledgeRetriever, SearchHit


class RerankingKnowledgeRetriever:
    """Keep course isolation in retrieval and limit MaaS to ordering its candidates."""

    def __init__(
        self,
        retriever: KnowledgeRetriever,
        reranker: DocumentReranker,
        *,
        candidate_limit: int = 12,
        max_document_chars: int = 8000,
    ) -> None:
        if (
            isinstance(candidate_limit, bool)
            or not isinstance(candidate_limit, int)
            or not 1 <= candidate_limit <= 20
        ):
            raise ValueError("candidate_limit must be between 1 and 20")
        if max_document_chars < 1:
            raise ValueError("max_document_chars must be positive")
        self._retriever = retriever
        self._reranker = reranker
        self._candidate_limit = candidate_limit
        self._max_document_chars = max_document_chars

    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        if not query.strip() or top_k <= 0:
            return ()
        candidates = tuple(
            await self._retriever.search(query, course_id, max(top_k, self._candidate_limit))
        )
        if not candidates:
            return ()
        pool = candidates[: self._candidate_limit]
        if any(len(hit.content) > self._max_document_chars for hit in pool):
            return self._degraded(candidates[:top_k], "candidate_too_long")
        try:
            ranked = await self._reranker.rerank(
                query=query,
                documents=[hit.content for hit in pool],
            )
            if not isinstance(ranked, (tuple, list)) or not 1 <= len(ranked) <= len(pool):
                raise ModelUpstreamError("MaaS reranker returned invalid ranks")
            seen: set[int] = set()
            validated: list[RankedDocument] = []
            for rank in ranked:
                if (
                    not isinstance(rank, RankedDocument)
                    or isinstance(rank.index, bool)
                    or not isinstance(rank.index, int)
                    or not 0 <= rank.index < len(pool)
                    or rank.index in seen
                    or isinstance(rank.score, bool)
                    or not isinstance(rank.score, (int, float))
                ):
                    raise ModelUpstreamError("MaaS reranker returned invalid ranks")
                try:
                    score = float(rank.score)
                except OverflowError:
                    raise ModelUpstreamError("MaaS reranker returned invalid ranks") from None
                if not math.isfinite(score):
                    raise ModelUpstreamError("MaaS reranker returned invalid ranks")
                seen.add(rank.index)
                validated.append(RankedDocument(index=rank.index, score=score))
            ordered = [
                replace(
                    pool[rank.index],
                    metadata={
                        **pool[rank.index].metadata,
                        "rerank_provider": "xfyun-maas",
                        "rerank_status": "completed",
                        "rerank_score": rank.score,
                    },
                )
                for rank in sorted(validated, key=lambda item: (-item.score, item.index))
            ]
            # Provider subsets must not silently discard valid retrieved evidence.
            ordered.extend(
                replace(
                    hit,
                    metadata={
                        **hit.metadata,
                        "rerank_provider": "xfyun-maas",
                        "rerank_status": "completed",
                        "rerank_scored": False,
                    },
                )
                for index, hit in enumerate(candidates)
                if index not in seen
            )
            return tuple(ordered[:top_k])
        except ModelError as error:
            return self._degraded(candidates[:top_k], error.code)

    @staticmethod
    def _degraded(hits: Sequence[SearchHit], reason: str) -> tuple[SearchHit, ...]:
        return tuple(
            replace(
                hit,
                metadata={
                    **hit.metadata,
                    "rerank_provider": "xfyun-maas",
                    "rerank_status": "degraded",
                    "rerank_reason": reason,
                },
            )
            for hit in hits
        )
