from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


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
