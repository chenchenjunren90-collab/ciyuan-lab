"""Typed persistence inputs kept separate from scoring policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

CourseId = Literal["c", "python", "data_structures"]
LearningEventType = Literal[
    "assessment.completed",
    "practice.submitted",
    "code.verified",
    "profile.updated",
    "recommendation.generated",
]


@dataclass(frozen=True, slots=True)
class CourseVersion:
    course_id: CourseId
    version: str
    title: str
    status: str
    manifest_hash: str
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class LearningEvent:
    event_id: UUID
    schema_version: str
    event_type: LearningEventType
    occurred_at: datetime
    student_id: str
    course_id: CourseId
    course_version: str
    payload: dict[str, object]
    knowledge_point_id: str | None = None
    trace_id: str | None = None
    evidence_summary: str | None = None
