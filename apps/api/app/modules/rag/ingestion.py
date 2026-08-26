"""Traceable knowledge-ingestion planning with explicit review gates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

from app.modules.course_content import CourseId, CoursePackRepository
from app.modules.rag.retriever import split_source


@dataclass(frozen=True, slots=True)
class IngestionCandidate:
    candidate_id: str
    course_id: CourseId
    record_type: Literal["reviewed_source_chunk", "concept_preview"]
    record_id: str
    source_ids: tuple[str, ...]
    content_hash: str
    character_count: int
    eligible: bool
    blocked_reason: str | None


@dataclass(frozen=True, slots=True)
class IngestionPlan:
    schema_version: str
    snapshot_hash: str
    eligible_count: int
    blocked_count: int
    candidates: tuple[IngestionCandidate, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"


@dataclass(frozen=True, slots=True)
class EligibleKnowledgeChunk:
    """Reviewed evidence payload that may be written to the retrieval index."""

    chunk_id: str
    source_id: str
    course_id: CourseId
    title: str
    citation: dict[str, object]
    content: str
    content_hash: str


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_ingestion_plan(repository: CoursePackRepository) -> IngestionPlan:
    candidates: list[IngestionCandidate] = []
    for course_id in ("c", "python", "data_structures"):
        for source in repository.list_rag_source_records(course_id):
            for index, content in enumerate(split_source(source), start=1):
                digest = _digest(content)
                candidates.append(
                    IngestionCandidate(
                        candidate_id=f"source:{source.id}:{index:03d}:{digest[:10]}",
                        course_id=course_id,
                        record_type="reviewed_source_chunk",
                        record_id=source.id,
                        source_ids=(source.id,),
                        content_hash=digest,
                        character_count=len(content),
                        eligible=True,
                        blocked_reason=None,
                    )
                )

        for concept in repository.list_knowledge_points(course_id):
            detail = repository.get_knowledge_point(course_id, concept.id)
            lesson_text = json.dumps(detail.lesson, ensure_ascii=False, sort_keys=True)
            digest = _digest(lesson_text)
            blocked_reason = None if detail.status == "reviewed" else "concept_not_human_reviewed"
            candidates.append(
                IngestionCandidate(
                    candidate_id=f"concept:{detail.id}:{digest[:10]}",
                    course_id=course_id,
                    record_type="concept_preview",
                    record_id=detail.id,
                    source_ids=tuple(detail.source_refs),
                    content_hash=digest,
                    character_count=len(lesson_text),
                    eligible=blocked_reason is None,
                    blocked_reason=blocked_reason,
                )
            )

    ordered = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    snapshot_payload = "\n".join(
        f"{item.candidate_id}:{item.content_hash}:{item.eligible}" for item in ordered
    )
    return IngestionPlan(
        schema_version="0.1.0",
        snapshot_hash=_digest(snapshot_payload),
        eligible_count=sum(item.eligible for item in ordered),
        blocked_count=sum(not item.eligible for item in ordered),
        candidates=ordered,
    )


def build_eligible_chunks(
    repository: CoursePackRepository,
) -> tuple[EligibleKnowledgeChunk, ...]:
    """Build only reviewed and explicitly RAG-eligible source chunks."""

    chunks: list[EligibleKnowledgeChunk] = []
    for course_id in ("c", "python", "data_structures"):
        for source in repository.list_rag_source_records(course_id):
            for index, content in enumerate(split_source(source), start=1):
                digest = _digest(content)
                chunks.append(
                    EligibleKnowledgeChunk(
                        chunk_id=f"source:{source.id}:{index:03d}:{digest[:10]}",
                        source_id=source.id,
                        course_id=course_id,
                        title=source.title,
                        citation={str(key): value for key, value in source.citation.items()},
                        content=content,
                        content_hash=digest,
                    )
                )
    return tuple(sorted(chunks, key=lambda item: item.chunk_id))
