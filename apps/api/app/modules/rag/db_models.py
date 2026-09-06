"""Metadata for the existing reviewed-evidence table (migration 20260825_0003).

Registering this table in the shared metadata prevents Alembic autogeneration
from treating the live knowledge index as an unmanaged table to be dropped.
"""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import CheckConstraint, Computed, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.learner_profile.db_models import Base


class KnowledgeChunkRow(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        CheckConstraint(
            "course_id IN ('c', 'python', 'data_structures')", name="course_id_allowed"
        ),
        Index("ix_knowledge_chunks_course_id", "course_id"),
        Index("ix_knowledge_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_knowledge_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    chunk_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(100))
    course_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(300))
    citation: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    lexical_tokens: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(384))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', lexical_tokens)", persisted=True)
    )
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
