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
MasteryReasonCode = Literal[
    "assessment_result",
    "practice_result",
    "code_test_ratio",
    "insufficient_evidence",
    "unsupported_event",
]
RecommendationReasonCode = Literal[
    "needs_reinforcement",
    "insufficient_evidence",
    "continue_practice",
    "ready_to_progress",
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


@dataclass(frozen=True, slots=True)
class MasterySnapshot:
    """Current persisted state supplied to a pure mastery policy."""

    score: float
    evidence_count: int
    revision: int


@dataclass(frozen=True, slots=True)
class MasteryDecision:
    """Versioned decision produced from one immutable learning event."""

    knowledge_point_id: str
    score: float
    evidence_count: int
    revision: int
    evidence_value: float
    evidence_weight: float
    policy_version: str
    reason_code: MasteryReasonCode


@dataclass(frozen=True, slots=True)
class MasteryRejection:
    """A stored event that cannot legitimately change mastery."""

    reason_code: Literal["insufficient_evidence", "unsupported_event"]


@dataclass(frozen=True, slots=True)
class MasteryUpdateResult:
    """Result of atomically projecting an event into mastery state."""

    event_id: UUID
    applied: bool
    duplicate: bool
    reason_code: MasteryReasonCode
    knowledge_point_id: str | None = None
    previous_score: float | None = None
    new_score: float | None = None
    previous_evidence_count: int = 0
    new_evidence_count: int = 0
    revision: int | None = None
    policy_version: str | None = None


@dataclass(frozen=True, slots=True)
class MasteryAuditRecord:
    event_id: UUID
    student_id: str
    course_id: CourseId
    knowledge_point_id: str
    previous_score: float | None
    new_score: float
    previous_evidence_count: int
    new_evidence_count: int
    revision: int
    evidence_value: float
    evidence_weight: float
    policy_version: str
    reason_code: MasteryReasonCode
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecommendationCandidate:
    """Explainable input for AGENT-01; it is not an LLM-selected activity."""

    knowledge_point_id: str
    score: float
    evidence_count: int
    confidence: float
    priority: float
    reason_code: RecommendationReasonCode
