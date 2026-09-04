import math

import pytest

from app.modules.course_content import CoursePackRepository
from app.modules.rag.embeddings import TokenHashEmbedder
from app.modules.rag.ingestion import build_eligible_chunks, build_ingestion_plan
from app.modules.rag.pgvector_retriever import PgVectorKnowledgeRetriever
from app.modules.rag.retriever import query_is_in_course_scope, query_variants, tokenize


def test_cjk_tokenization_does_not_emit_single_character_noise() -> None:
    tokens = tokenize("民法典关于租赁合同如何规定")

    assert "民法典关于租赁合同如何规定" in tokens
    assert "民法" in tokens
    assert "如何" in tokens
    assert "法" not in tokens
    assert "如" not in tokens


def test_compound_question_produces_bounded_clause_variants() -> None:
    variants = query_variants("BFS 为什么使用队列？Dijkstra 对权重有什么要求？")

    assert variants == (
        "BFS 为什么使用队列？Dijkstra 对权重有什么要求？",
        "BFS 为什么使用队列",
        "Dijkstra 对权重有什么要求",
        "bfs",
        "dijkstra",
        "队列",
        "权重",
    )


def test_natural_language_question_keeps_code_identifier_as_its_own_variant() -> None:
    variants = query_variants("我还没太懂 print 是什么意思，能再讲一下吗？")

    assert "print" in variants


def test_natural_language_question_keeps_cjk_technical_term_as_its_own_variant() -> None:
    variants = query_variants("Python 字典是什么？")

    assert "字典" in variants


@pytest.mark.parametrize(
    ("course_id", "question", "expected"),
    [
        ("c", "Python 默认参数在什么时候求值", False),
        ("c", "散列表冲突如何处理", False),
        ("data_structures", "C printf 格式说明符如何匹配类型", False),
        ("python", "Python 数据清洗如何保留异常原因", True),
        ("c", "变量为什么必须先初始化", True),
    ],
)
def test_explicit_foreign_course_markers_are_rejected(
    course_id: str, question: str, expected: bool
) -> None:
    assert query_is_in_course_scope(question, course_id) is expected


def test_token_hash_embedding_is_deterministic_and_normalized() -> None:
    embedder = TokenHashEmbedder()
    first = embedder.embed("Python 列表与字典")
    second = embedder.embed("Python 列表与字典")

    assert first == second
    assert len(first) == 384
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)
    assert embedder.embed("") == [0.0] * 384


def test_eligible_chunks_match_reviewed_source_side_of_manifest() -> None:
    repository = CoursePackRepository()
    chunks = build_eligible_chunks(repository)
    plan = build_ingestion_plan(repository)
    expected_source_chunks = sum(
        candidate.eligible and candidate.record_type == "reviewed_source_chunk"
        for candidate in plan.candidates
    )

    assert len(chunks) == expected_source_chunks
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert {chunk.course_id for chunk in chunks} == {"c", "python", "data_structures"}
    assert all(chunk.source_id.startswith("SRC-") for chunk in chunks)
    assert all(len(chunk.content_hash) == 64 for chunk in chunks)


def test_pgvector_retriever_validates_weight_before_opening_database() -> None:
    with pytest.raises(ValueError, match="vector_weight"):
        PgVectorKnowledgeRetriever(object(), vector_weight=1.1)  # type: ignore[arg-type]
