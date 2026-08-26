import asyncio
import os

import pytest
from alembic import command
from alembic.config import Config

from app.core.database import create_database_engine
from app.modules.course_content import CoursePackRepository
from app.modules.rag.ingestion import build_eligible_chunks
from app.modules.rag.pgvector_retriever import (
    PgVectorKnowledgeRetriever,
    PgVectorKnowledgeStore,
)

_DATABASE_URL = os.getenv("CIYUAN_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL,
    reason="CIYUAN_TEST_DATABASE_URL is required for real pgvector acceptance",
)


def test_reviewed_chunks_can_be_synchronized_and_course_isolated() -> None:
    assert _DATABASE_URL is not None
    config = Config("alembic.ini")
    config.attributes["database_url"] = _DATABASE_URL
    command.upgrade(config, "head")

    engine = create_database_engine(_DATABASE_URL)
    chunks = build_eligible_chunks(CoursePackRepository())
    assert PgVectorKnowledgeStore(engine).synchronize(chunks) == len(chunks)

    retriever = PgVectorKnowledgeRetriever(engine)
    hits = asyncio.run(retriever.search("Python 容器 顺序 唯一性 键值关联", "python", 5))

    assert hits
    assert all(hit.source_id.startswith("SRC-PY-") for hit in hits)
    assert all(hit.score >= 0.10 for hit in hits)
