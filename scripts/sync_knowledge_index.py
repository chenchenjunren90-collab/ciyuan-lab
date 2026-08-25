"""Synchronize reviewed course evidence into PostgreSQL/pgvector."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.database import create_database_engine
from app.modules.course_content import CoursePackRepository
from app.modules.rag.ingestion import build_eligible_chunks
from app.modules.rag.pgvector_retriever import PgVectorKnowledgeStore


def main() -> int:
    settings = get_settings()
    chunks = build_eligible_chunks(CoursePackRepository())
    count = PgVectorKnowledgeStore(create_database_engine(settings.database_url)).synchronize(
        chunks
    )
    print(f"Synchronized {count} reviewed chunks into knowledge_chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
