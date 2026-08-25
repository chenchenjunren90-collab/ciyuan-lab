"""Retrieval-augmented generation boundary."""

from app.modules.rag.ingestion import IngestionCandidate, IngestionPlan, build_ingestion_plan
from app.modules.rag.models import Citation, QaRequest, QaResponse
from app.modules.rag.ports import KnowledgeRetriever, SearchHit
from app.modules.rag.retriever import LexicalKnowledgeRetriever

__all__ = [
    "Citation",
    "IngestionCandidate",
    "IngestionPlan",
    "KnowledgeRetriever",
    "LexicalKnowledgeRetriever",
    "QaRequest",
    "QaResponse",
    "build_ingestion_plan",
    "SearchHit",
]
