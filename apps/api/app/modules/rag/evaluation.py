"""Reproducible retrieval evaluation without invoking a generative model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from app.modules.course_content import CourseId
from app.modules.rag.ports import KnowledgeRetriever

QueryKind = Literal["answerable", "unanswerable", "cross_course"]


@dataclass(frozen=True, slots=True)
class RetrievalEvalCase:
    id: str
    course_id: CourseId
    query: str
    kind: QueryKind
    expected_source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalEvalResult:
    dataset_size: int
    answerable_count: int
    recall_at_k: float
    mean_reciprocal_rank: float
    unanswerable_rejection_rate: float
    cross_course_rejection_rate: float
    course_isolation_rate: float
    failures: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"


def load_eval_cases(path: Path) -> tuple[RetrievalEvalCase, ...]:
    cases: list[RetrievalEvalCase] = []
    allowed_courses = {"c", "python", "data_structures"}
    allowed_kinds = {"answerable", "unanswerable", "cross_course"}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        try:
            case = RetrievalEvalCase(
                id=str(value["id"]),
                course_id=value["course_id"],
                query=str(value["query"]),
                kind=value["kind"],
                expected_source_ids=tuple(value.get("expected_source_ids", [])),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"invalid eval case at line {line_number}") from exc
        if (
            not case.id.strip()
            or not case.query.strip()
            or case.course_id not in allowed_courses
            or case.kind not in allowed_kinds
            or (case.kind == "answerable" and not case.expected_source_ids)
        ):
            raise ValueError(f"invalid eval case at line {line_number}")
        cases.append(case)
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("eval case ids must be unique")
    return tuple(cases)


async def evaluate_retriever(
    retriever: KnowledgeRetriever,
    cases: tuple[RetrievalEvalCase, ...],
    *,
    top_k: int = 5,
) -> RetrievalEvalResult:
    answerable = 0
    recalled = 0
    reciprocal_rank = 0.0
    unanswerable = 0
    unanswerable_rejected = 0
    cross_course = 0
    cross_course_rejected = 0
    isolated = 0
    failures: list[str] = []
    prefixes = {
        "c": "SRC-C-",
        "python": "SRC-PY-",
        "data_structures": "SRC-DS-",
    }

    for case in cases:
        hits = await retriever.search(case.query, case.course_id, top_k)
        returned = [hit.source_id for hit in hits]
        is_isolated = all(source_id.startswith(prefixes[case.course_id]) for source_id in returned)
        isolated += int(is_isolated)
        if not is_isolated:
            failures.append(f"{case.id}:cross_course_source")

        if case.kind == "answerable":
            answerable += 1
            rank = next(
                (
                    index
                    for index, source_id in enumerate(returned, start=1)
                    if source_id in case.expected_source_ids
                ),
                None,
            )
            if rank is None:
                failures.append(f"{case.id}:expected_source_not_retrieved")
            else:
                recalled += 1
                reciprocal_rank += 1.0 / rank
        elif case.kind == "unanswerable":
            unanswerable += 1
            unanswerable_rejected += int(not hits)
            if hits:
                failures.append(f"{case.id}:false_positive")
        else:
            cross_course += 1
            cross_course_rejected += int(not hits)
            if hits:
                failures.append(f"{case.id}:cross_course_query_not_rejected")

    total = len(cases)
    return RetrievalEvalResult(
        dataset_size=total,
        answerable_count=answerable,
        recall_at_k=round(recalled / answerable if answerable else 0.0, 4),
        mean_reciprocal_rank=round(reciprocal_rank / answerable if answerable else 0.0, 4),
        unanswerable_rejection_rate=round(
            unanswerable_rejected / unanswerable if unanswerable else 0.0, 4
        ),
        cross_course_rejection_rate=round(
            cross_course_rejected / cross_course if cross_course else 0.0, 4
        ),
        course_isolation_rate=round(isolated / total if total else 0.0, 4),
        failures=tuple(failures),
    )
