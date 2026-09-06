"""Exercise database failure and event-loop behavior without connecting to a database."""

import asyncio
import hashlib
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import OperationalError

from app.modules.learner_profile.db_models import Base
from app.modules.model_adapters.errors import ModelTimeoutError
from app.modules.orchestration.supervisor import QualitySupervisor, SupervisionResult
from app.modules.orchestration.tutor import TutorDraft
from app.modules.rag.db_models import KnowledgeChunkRow
from app.modules.rag.embeddings import TokenHashEmbedder
from app.modules.rag.ingestion import EligibleKnowledgeChunk
from app.modules.rag.pgvector_retriever import (
    PgVectorKnowledgeRetriever,
    PgVectorKnowledgeStore,
    _vector_literal,
)
from app.modules.rag.ports import KnowledgeRetrievalError, SearchHit
from app.modules.rag.service import RagQaService


class RecordingEngine:
    def __init__(self, scores: tuple[float, ...] = (0.7,)) -> None:
        self.scores = scores
        self.thread_ids: list[int] = []
        self.statements: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def connect(self):  # type: ignore[no-untyped-def]
        self.thread_ids.append(threading.get_ident())
        yield self

    def execute(self, statement: Any, parameters: dict[str, Any]) -> "RecordingEngine":
        self.statements.append((str(statement), parameters))
        return self

    def mappings(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": "SRC-PY-TEST",
                "chunk_id": f"chunk-{index}",
                "content": "列表可变。",
                "title": "列表",
                "citation": {"locator": "测试资料"},
                "score": score,
            }
            for index, score in enumerate(self.scores)
        ]


def test_sync_database_work_runs_off_event_loop_and_bounds_scores() -> None:
    engine = RecordingEngine((1.0000002, float("nan"), 0.8))
    main_thread = threading.get_ident()
    retriever = PgVectorKnowledgeRetriever(engine)  # type: ignore[arg-type]

    hits = asyncio.run(retriever.search("Python 列表", "python", 5))

    assert [hit.score for hit in hits] == [1.0, 0.8]
    assert engine.thread_ids and all(thread != main_thread for thread in engine.thread_ids)
    assert all(hit.metadata["course_id"] == "python" for hit in hits)
    timeout_query, timeout_args = engine.statements[0]
    assert "set_config('statement_timeout'" in timeout_query
    assert timeout_args == {"timeout_ms": "3000"}
    for query, parameters in engine.statements[1:]:
        assert "32\n" in query  # PostgreSQL rank/(rank+1) normalization.
        assert "WHERE course_id = :course_id" in query
        assert parameters["course_id"] == "python"


class BrokenEngine:
    def connect(self) -> None:
        raise OperationalError("SELECT private_details", {}, Exception("private connection data"))


def test_driver_failure_is_a_sanitized_distinct_error() -> None:
    retriever = PgVectorKnowledgeRetriever(BrokenEngine())  # type: ignore[arg-type]

    with pytest.raises(KnowledgeRetrievalError) as failure:
        asyncio.run(retriever.search("Python 列表", "python", 5))

    assert str(failure.value) == "knowledge index is temporarily unavailable"
    assert "private" not in str(failure.value)


def test_qa_does_not_call_model_when_knowledge_database_fails() -> None:
    service = RagQaService(
        PgVectorKnowledgeRetriever(BrokenEngine()),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
    )

    result = asyncio.run(service.answer(course_id="python", question="Python 列表是什么"))

    assert result.status == "insufficient_evidence"
    assert result.citations == []
    assert result.trace[0].status == "degraded"
    assert "暂时不可用" in result.answer
    assert "private" not in result.model_dump_json()


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan")])
def test_invalid_threshold_is_rejected_without_connecting(score: float) -> None:
    with pytest.raises(ValueError, match="min_score"):
        PgVectorKnowledgeRetriever(BrokenEngine(), min_score=score)  # type: ignore[arg-type]


def test_embedder_dimensions_must_match_existing_index() -> None:
    for cls in (PgVectorKnowledgeRetriever, PgVectorKnowledgeStore):
        with pytest.raises(ValueError, match="dimensions"):
            cls(BrokenEngine(), TokenHashEmbedder(768))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        _vector_literal([float("inf")] * 384)


def test_migration_target_metadata_keeps_the_existing_knowledge_index() -> None:
    table = Base.metadata.tables["knowledge_chunks"]
    assert table is KnowledgeChunkRow.__table__
    assert table.c.embedding.type.dim == TokenHashEmbedder().dimensions
    assert {index.name for index in table.indexes} == {
        "ix_knowledge_chunks_course_id",
        "ix_knowledge_chunks_search_vector",
        "ix_knowledge_chunks_embedding_hnsw",
    }


def test_invalid_snapshot_is_rejected_before_starting_transaction() -> None:
    chunk = EligibleKnowledgeChunk(
        chunk_id="chunk-1",
        source_id="SRC-PY-TEST",
        course_id="python",
        title="列表",
        citation={},
        content="列表可变。",
        content_hash=hashlib.sha256("列表可变。".encode()).hexdigest(),
    )
    store = PgVectorKnowledgeStore(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="duplicate"):
        store.synchronize((chunk, chunk))
    invalid = EligibleKnowledgeChunk(
        chunk_id="chunk-2",
        source_id=chunk.source_id,
        course_id=chunk.course_id,
        title=chunk.title,
        citation={},
        content="已被改写的内容",
        content_hash=chunk.content_hash,
    )
    with pytest.raises(ValueError, match="hash"):
        store.synchronize((invalid,))


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [((), None), (("completed",), "completed"), (("completed", "degraded"), "degraded")],
)
def test_qa_reports_reranking_status_without_exposing_provider_details(
    statuses: tuple[str, ...], expected: str | None
) -> None:
    hits = tuple(
        SearchHit(
            source_id="SRC-PY-TEST",
            chunk_id=f"chunk-{index}",
            content="列表可变。",
            score=0.7,
            metadata={"rerank_status": status, "rerank_reason": "private upstream reason"},
        )
        for index, status in enumerate(statuses or (None,))
    )
    service = RagQaService(
        SimpleNamespace(search=AsyncMock(return_value=hits)),
        SimpleNamespace(
            draft=AsyncMock(return_value=TutorDraft("列表可变。", (hits[0].chunk_id,), False))
        ),
        QualitySupervisor(),
    )

    result = asyncio.run(service.answer(course_id="python", question="列表是否可变"))

    retrieval_steps = [step for step in result.trace if step.component == "retrieval"]
    assert len(retrieval_steps) == (1 if expected is None else 2)
    if expected is not None:
        assert retrieval_steps[1].status == expected
    assert "private upstream reason" not in result.model_dump_json()
    assert result.citations[0].chunk_id == "chunk-0"


@pytest.mark.parametrize(
    ("reason", "degraded"),
    [
        ("semantic_review_unavailable", True),
        ("semantic_invalid_verdict", True),
        ("semantic_unsupported_claim", False),
    ],
)
def test_qa_distinguishes_unavailable_review_from_a_rejected_answer(
    reason: str, degraded: bool
) -> None:
    hit = SearchHit("SRC-PY-TEST", "chunk-1", "列表可变。", 0.7, {})
    service = RagQaService(
        SimpleNamespace(search=AsyncMock(return_value=(hit,))),
        SimpleNamespace(
            draft=AsyncMock(return_value=TutorDraft("尚未审核的回答", (hit.chunk_id,), False))
        ),
        SimpleNamespace(
            review=AsyncMock(
                return_value=SupervisionResult(
                    accepted=False,
                    answer="",
                    citations=(),
                    reason_code=reason,
                    model_degraded=degraded,
                )
            )
        ),
    )

    result = asyncio.run(service.answer(course_id="python", question="列表是否可变"))

    assert result.status == "insufficient_evidence"
    assert result.answer == ("质量审核暂时不可用，请稍后重试。" if degraded else "")
    assert result.citations == []
    assert result.trace[-1].status == ("degraded" if degraded else "blocked")
    assert "尚未审核的回答" not in result.model_dump_json()


def test_qa_fails_closed_when_configured_semantic_reviewer_times_out() -> None:
    hit = SearchHit("SRC-PY-TEST", "chunk-1", "列表可变。", 0.7, {})
    review_model = SimpleNamespace(
        complete=AsyncMock(side_effect=ModelTimeoutError("private provider response"))
    )
    service = RagQaService(
        SimpleNamespace(search=AsyncMock(return_value=(hit,))),
        SimpleNamespace(
            draft=AsyncMock(return_value=TutorDraft("未经语义审核的草稿", (hit.chunk_id,), False))
        ),
        QualitySupervisor(review_model),
    )

    result = asyncio.run(service.answer(course_id="python", question="列表是否可变"))

    assert review_model.complete.await_count == 1
    assert result.answer == "质量审核暂时不可用，请稍后重试。"
    assert result.status == "insufficient_evidence"
    assert result.citations == []
    assert result.trace[-1].status == "degraded"
    assert "private provider response" not in result.model_dump_json()
    assert "未经语义审核的草稿" not in result.model_dump_json()
