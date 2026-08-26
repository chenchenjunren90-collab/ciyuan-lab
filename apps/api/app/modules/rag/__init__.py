"""Retrieval-augmented generation boundary."""

from app.modules.rag.embeddings import TokenHashEmbedder
from app.modules.rag.ingestion import (
    EligibleKnowledgeChunk,
    IngestionCandidate,
    IngestionPlan,
    build_eligible_chunks,
    build_ingestion_plan,
)
from app.modules.rag.models import Citation, QaRequest, QaResponse
from app.modules.rag.pgvector_retriever import (
    PgVectorKnowledgeRetriever,
    PgVectorKnowledgeStore,
)
from app.modules.rag.ports import KnowledgeRetriever, SearchHit
from app.modules.rag.retriever import LexicalKnowledgeRetriever

__all__ = [
    "Citation",
    "EligibleKnowledgeChunk",
    "IngestionCandidate",
    "IngestionPlan",
    "KnowledgeRetriever",
    "LexicalKnowledgeRetriever",
    "PgVectorKnowledgeRetriever",
    "PgVectorKnowledgeStore",
    "QaRequest",
    "QaResponse",
    "TokenHashEmbedder",
    "build_eligible_chunks",
    "build_ingestion_plan",
    "SearchHit",
]
