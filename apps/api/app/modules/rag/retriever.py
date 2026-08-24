"""Deterministic, course-isolated retrieval for the offline MVP."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.modules.course_content import CourseId, CoursePackRepository, RagSourceRecord
from app.modules.rag.ports import KnowledgeRetriever, SearchHit

ASCII_WORD = re.compile(r"[a-z0-9_+#.-]+")
CJK_RUN = re.compile(r"[\u3400-\u9fff]+")


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    source_id: str
    chunk_id: str
    course_id: CourseId
    title: str
    citation: dict[str, object]
    content: str
    term_counts: Counter[str]


def tokenize(text: str) -> Counter[str]:
    """Tokenize mixed Chinese/programming text without an external segmenter."""

    normalized = text.casefold()
    tokens = ASCII_WORD.findall(normalized)
    for run in CJK_RUN.findall(normalized):
        tokens.extend(run)
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return Counter(token for token in tokens if token.strip())


def split_source(source: RagSourceRecord, *, max_chars: int = 360) -> Iterable[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", source.text) if part.strip()]
    for paragraph in paragraphs:
        sentences = [
            part.strip() for part in re.split(r"(?<=[。！？；])", paragraph) if part.strip()
        ]
        buffer = ""
        for sentence in sentences:
            if buffer and len(buffer) + len(sentence) > max_chars:
                yield buffer
                buffer = sentence
            else:
                buffer += sentence
        if buffer:
            yield buffer


class LexicalKnowledgeRetriever(KnowledgeRetriever):
    """Small deterministic index; the port can later be backed by pgvector."""

    def __init__(self, chunks: Sequence[IndexedChunk], *, min_score: float = 0.10) -> None:
        self._chunks = tuple(chunks)
        self._min_score = min_score

    @classmethod
    def from_repository(cls, courses: CoursePackRepository) -> LexicalKnowledgeRetriever:
        chunks: list[IndexedChunk] = []
        for course_id in ("c", "python", "data_structures"):
            for source in courses.list_rag_source_records(course_id):
                for index, content in enumerate(split_source(source), start=1):
                    digest = hashlib.sha256(content.encode()).hexdigest()[:10]
                    chunks.append(
                        IndexedChunk(
                            source_id=source.id,
                            chunk_id=f"{source.id}-{index:03d}-{digest}",
                            course_id=course_id,
                            title=source.title,
                            citation={str(key): value for key, value in source.citation.items()},
                            content=content,
                            term_counts=tokenize(f"{source.title} {content}"),
                        )
                    )
        return cls(chunks)

    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        if not query.strip() or top_k < 1:
            return ()
        query_terms = tokenize(query)
        if not query_terms:
            return ()
        ranked: list[tuple[float, IndexedChunk]] = []
        for chunk in self._chunks:
            if chunk.course_id != course_id:
                continue
            score = self._cosine(query_terms, chunk.term_counts)
            if score >= self._min_score:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return tuple(
            SearchHit(
                source_id=chunk.source_id,
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                score=round(score, 6),
                metadata={"title": chunk.title, "citation": chunk.citation},
            )
            for score, chunk in ranked[: min(top_k, 10)]
        )

    @staticmethod
    def _cosine(left: Counter[str], right: Counter[str]) -> float:
        shared = set(left) & set(right)
        if not shared:
            return 0.0
        numerator = sum(left[token] * right[token] for token in shared)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0
