from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


class KnowledgeRetrievalError(RuntimeError):
    """The evidence backend is unavailable; this is not an empty search result."""


class TextEmbedder(Protocol):
    """Synchronous embedding port; provider and index dimensions must match."""

    dimensions: int

    def embed(self, text: str) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class SearchHit:
    source_id: str
    chunk_id: str
    content: str
    score: float
    metadata: Mapping[str, object]


class KnowledgeRetriever(Protocol):
    """Retrieves reviewable course evidence for a response."""

    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]: ...
