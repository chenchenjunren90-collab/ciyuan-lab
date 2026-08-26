"""AGENT-03: deterministic safety and citation gate before student delivery."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.orchestration.tutor import TutorDraft
from app.modules.rag.ports import SearchHit

_SECRET_PATTERNS = (
    re.compile(r"(?i)api[_ -]?key\s*[:=]"),
    re.compile(r"(?i)api[_ -]?secret\s*[:=]"),
    re.compile(r"(?i)authorization\s*:\s*bearer"),
    re.compile(r"(?i)system\s+prompt"),
)


@dataclass(frozen=True, slots=True)
class SupervisionResult:
    accepted: bool
    answer: str
    citations: tuple[SearchHit, ...]
    reason_code: str


class QualitySupervisor:
    """Checks facts and safety without calling a model or changing learner state."""

    def inspect(self, *, draft: TutorDraft, evidence: Sequence[SearchHit]) -> SupervisionResult:
        answer = draft.answer.strip()
        if not answer or len(answer) > 2000:
            return self._reject("invalid_answer")
        if any(pattern.search(answer) for pattern in _SECRET_PATTERNS):
            return self._reject("unsafe_content")

        by_chunk = {hit.chunk_id: hit for hit in evidence}
        if not draft.citation_chunk_ids:
            return self._reject("missing_citation")
        if any(chunk_id not in by_chunk for chunk_id in draft.citation_chunk_ids):
            return self._reject("fabricated_citation")
        citations = tuple(by_chunk[chunk_id] for chunk_id in draft.citation_chunk_ids)
        if not citations:
            return self._reject("missing_citation")
        return SupervisionResult(
            accepted=True,
            answer=answer,
            citations=citations,
            reason_code="accepted",
        )

    @staticmethod
    def _reject(reason_code: str) -> SupervisionResult:
        return SupervisionResult(
            accepted=False,
            answer="",
            citations=(),
            reason_code=reason_code,
        )
