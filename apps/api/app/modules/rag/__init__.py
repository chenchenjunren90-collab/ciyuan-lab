"""Retrieval-augmented generation boundary."""

from app.modules.rag.models import Citation, QaRequest, QaResponse
from app.modules.rag.ports import KnowledgeRetriever, SearchHit
from app.modules.rag.retriever import LexicalKnowledgeRetriever

__all__ = [
    "Citation",
    "KnowledgeRetriever",
    "LexicalKnowledgeRetriever",
    "QaRequest",
    "QaResponse",
    "SearchHit",
]
