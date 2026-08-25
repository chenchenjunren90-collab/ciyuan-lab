"""PostgreSQL/pgvector-backed reviewed-evidence index and hybrid retriever."""

from __future__ import annotations

import json
from collections.abc import Sequence

from sqlalchemy import Engine, bindparam, text

from app.modules.rag.embeddings import TokenHashEmbedder
from app.modules.rag.ingestion import EligibleKnowledgeChunk
from app.modules.rag.ports import KnowledgeRetriever, SearchHit
from app.modules.rag.retriever import tokenize

_COURSE_IDS = ("c", "python", "data_structures")


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{value:.9f}" for value in values) + "]"


class PgVectorKnowledgeStore:
    """Synchronize the approved repository snapshot into one transaction."""

    def __init__(self, engine: Engine, embedder: TokenHashEmbedder | None = None) -> None:
        self._engine = engine
        self._embedder = embedder or TokenHashEmbedder()

    def synchronize(self, chunks: Sequence[EligibleKnowledgeChunk]) -> int:
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        statement = text(
            """
            INSERT INTO knowledge_chunks (
                chunk_id, source_id, course_id, title, citation, content,
                content_hash, lexical_tokens, embedding
            ) VALUES (
                :chunk_id, :source_id, :course_id, :title, CAST(:citation AS jsonb),
                :content, :content_hash, :lexical_tokens, CAST(:embedding AS vector)
            )
            ON CONFLICT (chunk_id) DO UPDATE SET
                source_id = EXCLUDED.source_id,
                course_id = EXCLUDED.course_id,
                title = EXCLUDED.title,
                citation = EXCLUDED.citation,
                content = EXCLUDED.content,
                content_hash = EXCLUDED.content_hash,
                lexical_tokens = EXCLUDED.lexical_tokens,
                embedding = EXCLUDED.embedding,
                indexed_at = now()
            """
        )
        with self._engine.begin() as connection:
            for chunk in chunks:
                lexical_tokens = " ".join(tokenize(f"{chunk.title} {chunk.content}"))
                connection.execute(
                    statement,
                    {
                        "chunk_id": chunk.chunk_id,
                        "source_id": chunk.source_id,
                        "course_id": chunk.course_id,
                        "title": chunk.title,
                        "citation": json.dumps(chunk.citation, ensure_ascii=False),
                        "content": chunk.content,
                        "content_hash": chunk.content_hash,
                        "lexical_tokens": lexical_tokens,
                        "embedding": _vector_literal(
                            self._embedder.embed(f"{chunk.title} {chunk.content}")
                        ),
                    },
                )
            cleanup = text(
                "DELETE FROM knowledge_chunks "
                "WHERE course_id IN :course_ids AND chunk_id NOT IN :chunk_ids"
            ).bindparams(
                bindparam("course_ids", expanding=True),
                bindparam("chunk_ids", expanding=True),
            )
            # Avoid an invalid empty ``NOT IN`` expression while still clearing a stale index.
            if chunk_ids:
                connection.execute(
                    cleanup,
                    {"course_ids": list(_COURSE_IDS), "chunk_ids": chunk_ids},
                )
            else:
                connection.execute(
                    text("DELETE FROM knowledge_chunks WHERE course_id IN :course_ids").bindparams(
                        bindparam("course_ids", expanding=True)
                    ),
                    {"course_ids": list(_COURSE_IDS)},
                )
        return len(chunks)


class PgVectorKnowledgeRetriever(KnowledgeRetriever):
    """Course-isolated hybrid retrieval over lexical rank and vector similarity."""

    def __init__(
        self,
        engine: Engine,
        embedder: TokenHashEmbedder | None = None,
        *,
        min_score: float = 0.10,
        vector_weight: float = 0.65,
    ) -> None:
        if not 0 <= vector_weight <= 1:
            raise ValueError("vector_weight must be between 0 and 1")
        self._engine = engine
        self._embedder = embedder or TokenHashEmbedder()
        self._min_score = min_score
        self._vector_weight = vector_weight

    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        if not query.strip() or course_id not in _COURSE_IDS or top_k < 1:
            return ()
        token_query = " ".join(tokenize(query))
        if not token_query:
            return ()
        vector = _vector_literal(self._embedder.embed(query))
        statement = text(
            """
            WITH scored AS (
                SELECT source_id, chunk_id, content, title, citation,
                       ts_rank_cd(
                           search_vector,
                           plainto_tsquery('simple', :token_query)
                       ) AS lexical_score,
                       GREATEST(0.0, 1.0 - (embedding <=> CAST(:embedding AS vector)))
                           AS vector_score
                FROM knowledge_chunks
                WHERE course_id = :course_id
            )
            SELECT source_id, chunk_id, content, title, citation,
                   (:vector_weight * vector_score
                    + (1.0 - :vector_weight) * lexical_score) AS score
            FROM scored
            WHERE lexical_score > 0 OR vector_score >= :min_score
            ORDER BY score DESC, chunk_id ASC
            LIMIT :top_k
            """
        )
        with self._engine.connect() as connection:
            rows = connection.execute(
                statement,
                {
                    "course_id": course_id,
                    "embedding": vector,
                    "token_query": token_query,
                    "vector_weight": self._vector_weight,
                    "min_score": self._min_score,
                    "top_k": min(top_k, 20),
                },
            ).mappings()
            return tuple(
                SearchHit(
                    source_id=str(row["source_id"]),
                    chunk_id=str(row["chunk_id"]),
                    content=str(row["content"]),
                    score=round(float(row["score"]), 6),
                    metadata={"title": row["title"], "citation": row["citation"]},
                )
                for row in rows
                if float(row["score"]) >= self._min_score
            )
