"""Add the reviewed-evidence pgvector retrieval index."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "20260825_0003"
down_revision: str | None = "20260822_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_chunks",
        sa.Column("chunk_id", sa.String(length=200), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("course_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("citation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("lexical_tokens", sa.Text(), nullable=False),
        sa.Column("embedding", VECTOR(dim=384), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', lexical_tokens)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "indexed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "course_id IN ('c', 'python', 'data_structures')",
            name=op.f("ck_knowledge_chunks_course_id_allowed"),
        ),
        sa.PrimaryKeyConstraint("chunk_id", name=op.f("pk_knowledge_chunks")),
    )
    op.create_index(
        "ix_knowledge_chunks_course_id",
        "knowledge_chunks",
        ["course_id"],
    )
    op.create_index(
        "ix_knowledge_chunks_search_vector",
        "knowledge_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_embedding_hnsw", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_search_vector", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_course_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
