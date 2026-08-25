import math

import pytest

from app.modules.course_content import CoursePackRepository
from app.modules.rag.embeddings import TokenHashEmbedder
from app.modules.rag.ingestion import build_eligible_chunks
from app.modules.rag.pgvector_retriever import PgVectorKnowledgeRetriever


def test_token_hash_embedding_is_deterministic_and_normalized() -> None:
    embedder = TokenHashEmbedder()
    first = embedder.embed("Python 列表与字典")
    second = embedder.embed("Python 列表与字典")

    assert first == second
    assert len(first) == 384
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)
    assert embedder.embed("") == [0.0] * 384


def test_eligible_chunks_match_reviewed_source_side_of_manifest() -> None:
    chunks = build_eligible_chunks(CoursePackRepository())

    assert len(chunks) == 13
    assert len({chunk.chunk_id for chunk in chunks}) == 13
    assert {chunk.course_id for chunk in chunks} == {"c", "python", "data_structures"}
    assert all(chunk.source_id.startswith("SRC-") for chunk in chunks)
    assert all(len(chunk.content_hash) == 64 for chunk in chunks)


def test_pgvector_retriever_validates_weight_before_opening_database() -> None:
    with pytest.raises(ValueError, match="vector_weight"):
        PgVectorKnowledgeRetriever(object(), vector_weight=1.1)  # type: ignore[arg-type]
