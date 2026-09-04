"""Synchronous repository with explicit transactions for learning evidence."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.modules.learner_profile.db_models import (
    CourseVersionRow,
    LearnerProfileRow,
    LearningEventRow,
    MasteryStateRow,
    MasteryUpdateAuditRow,
)
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.policy import MasteryPolicy
from app.modules.learner_profile.records import (
    CourseId,
    CourseVersion,
    LearningEvent,
    LearningEventType,
    MasteryAuditRecord,
    MasteryDecision,
    MasteryReasonCode,
    MasteryRejection,
    MasterySnapshot,
    MasteryUpdateResult,
)


class LearningRepository:
    """Persist facts only; mastery update policy belongs to DATA-02."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def register_course_version(self, course: CourseVersion) -> None:
        with self._session_factory.begin() as session:
            if course.is_active:
                for existing in session.scalars(
                    select(CourseVersionRow)
                    .where(CourseVersionRow.course_id == course.course_id)
                    .with_for_update()
                ):
                    existing.is_active = False

            session.execute(
                insert(CourseVersionRow)
                .values(
                    course_id=course.course_id,
                    version=course.version,
                    title=course.title,
                    status=course.status,
                    manifest_hash=course.manifest_hash,
                    is_active=course.is_active,
                )
                .on_conflict_do_update(
                    index_elements=[CourseVersionRow.course_id, CourseVersionRow.version],
                    set_={
                        "title": course.title,
                        "status": course.status,
                        "manifest_hash": course.manifest_hash,
                        "is_active": course.is_active,
                    },
                )
            )

    def get_active_course_version(self, course_id: CourseId) -> CourseVersion | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(CourseVersionRow).where(
                    CourseVersionRow.course_id == course_id,
                    CourseVersionRow.is_active.is_(True),
                )
            )
            if row is None:
                return None
            return CourseVersion(
                course_id=course_id,
                version=row.version,
                title=row.title,
                status=row.status,
                manifest_hash=row.manifest_hash,
                is_active=row.is_active,
            )

    def create_profile(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        course_version: str,
    ) -> None:
        self._validate_student_id(student_id)
        with self._session_factory.begin() as session:
            session.execute(
                insert(LearnerProfileRow)
                .values(
                    student_id=student_id,
                    course_id=course_id,
                    course_version=course_version,
                )
                .on_conflict_do_update(
                    index_elements=[
                        LearnerProfileRow.student_id,
                        LearnerProfileRow.course_id,
                    ],
                    set_={"course_version": course_version},
                )
            )

    def store_mastery_snapshot(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        knowledge_point_id: str,
        score: float,
        evidence_count: int,
        revision: int,
    ) -> None:
        """Store an already-decided snapshot without deciding how scores change."""

        if not 0 <= score <= 1:
            raise ValueError("score must be between 0 and 1")
        if evidence_count < 0:
            raise ValueError("evidence_count must be non-negative")
        if revision < 1:
            raise ValueError("revision must be positive")
        with self._session_factory.begin() as session:
            key = (student_id, course_id, knowledge_point_id)
            row = session.get(MasteryStateRow, key)
            if row is None:
                session.add(
                    MasteryStateRow(
                        student_id=student_id,
                        course_id=course_id,
                        knowledge_point_id=knowledge_point_id,
                        score=Decimal(str(score)),
                        evidence_count=evidence_count,
                        revision=revision,
                    )
                )
            else:
                row.score = Decimal(str(score))
                row.evidence_count = evidence_count
                row.revision = revision

    def append_event(self, event: LearningEvent) -> bool:
        """Append once by event_id; return False for a previously stored event."""

        self._validate_student_id(event.student_id)
        with self._session_factory.begin() as session:
            statement = (
                insert(LearningEventRow)
                .values(
                    event_id=event.event_id,
                    schema_version=event.schema_version,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at,
                    student_id=event.student_id,
                    course_id=event.course_id,
                    course_version=event.course_version,
                    knowledge_point_id=event.knowledge_point_id,
                    trace_id=event.trace_id,
                    payload=event.payload,
                    evidence_summary=event.evidence_summary,
                )
                .on_conflict_do_nothing(index_elements=[LearningEventRow.event_id])
                .returning(LearningEventRow.event_id)
            )
            inserted_event_id = session.scalar(statement)
            return inserted_event_id is not None

    def get_profile(self, *, student_id: str, course_id: CourseId) -> LearnerProfile | None:
        with self._session_factory() as session:
            profile_row = session.get(LearnerProfileRow, (student_id, course_id))
            if profile_row is None:
                return None
            mastery_rows = session.scalars(
                select(MasteryStateRow)
                .where(
                    MasteryStateRow.student_id == student_id,
                    MasteryStateRow.course_id == course_id,
                )
                .order_by(MasteryStateRow.knowledge_point_id)
            ).all()
            return LearnerProfile(
                student_id=student_id,
                course_id=course_id,
                mastery=[
                    MasteryState(
                        knowledge_point_id=row.knowledge_point_id,
                        score=float(row.score),
                        evidence_count=row.evidence_count,
                        updated_at=row.updated_at,
                    )
                    for row in mastery_rows
                ],
            )

    def list_events(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        limit: int = 100,
    ) -> Sequence[LearningEvent]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._session_factory() as session:
            rows = session.scalars(
                select(LearningEventRow)
                .where(
                    LearningEventRow.student_id == student_id,
                    LearningEventRow.course_id == course_id,
                )
                .order_by(LearningEventRow.occurred_at, LearningEventRow.event_id)
                .limit(limit)
            ).all()
            return tuple(
                LearningEvent(
                    event_id=row.event_id,
                    schema_version=row.schema_version,
                    event_type=cast(LearningEventType, row.event_type),
                    occurred_at=row.occurred_at,
                    student_id=row.student_id,
                    course_id=cast(CourseId, row.course_id),
                    course_version=row.course_version,
                    knowledge_point_id=row.knowledge_point_id,
                    trace_id=row.trace_id,
                    payload=dict(row.payload),
                    evidence_summary=row.evidence_summary,
                )
                for row in rows
            )

    def project_event(
        self,
        *,
        event_id: UUID,
        policy: MasteryPolicy,
    ) -> MasteryUpdateResult:
        """Atomically apply one stored event, serializing updates per learner/course."""

        with self._session_factory.begin() as session:
            event_row = session.scalar(
                select(LearningEventRow)
                .where(LearningEventRow.event_id == event_id)
                .with_for_update()
            )
            if event_row is None:
                raise LookupError(f"learning event not found: {event_id}")

            existing_audit = session.get(MasteryUpdateAuditRow, event_row.event_id)
            if existing_audit is not None:
                return self._audit_result(existing_audit, applied=False, duplicate=True)

            event = self._event_from_row(event_row)
            if not event.knowledge_point_id:
                return MasteryUpdateResult(
                    event_id=event.event_id,
                    applied=False,
                    duplicate=False,
                    reason_code="insufficient_evidence",
                )

            # The profile row is the serialization point for concurrent events that
            # may target a mastery row which does not exist yet.
            profile_row = session.scalar(
                select(LearnerProfileRow)
                .where(
                    LearnerProfileRow.student_id == event.student_id,
                    LearnerProfileRow.course_id == event.course_id,
                )
                .with_for_update()
            )
            if profile_row is None:
                raise LookupError("learner profile referenced by event was not found")

            mastery_row = session.scalar(
                select(MasteryStateRow)
                .where(
                    MasteryStateRow.student_id == event.student_id,
                    MasteryStateRow.course_id == event.course_id,
                    MasteryStateRow.knowledge_point_id == event.knowledge_point_id,
                )
                .with_for_update()
            )
            current = MasterySnapshot(
                score=float(mastery_row.score) if mastery_row is not None else policy.initial_score,
                evidence_count=mastery_row.evidence_count if mastery_row is not None else 0,
                revision=mastery_row.revision if mastery_row is not None else 0,
            )
            evaluation = policy.evaluate(event, current)
            if isinstance(evaluation, MasteryRejection):
                return MasteryUpdateResult(
                    event_id=event.event_id,
                    applied=False,
                    duplicate=False,
                    reason_code=evaluation.reason_code,
                    knowledge_point_id=event.knowledge_point_id,
                    previous_score=float(mastery_row.score) if mastery_row is not None else None,
                    new_score=float(mastery_row.score) if mastery_row is not None else None,
                    previous_evidence_count=current.evidence_count,
                    new_evidence_count=current.evidence_count,
                    revision=current.revision or None,
                    policy_version=policy.version,
                )

            self._validate_decision(event, current, evaluation)
            previous_score = float(mastery_row.score) if mastery_row is not None else None
            if mastery_row is None:
                mastery_row = MasteryStateRow(
                    student_id=event.student_id,
                    course_id=event.course_id,
                    knowledge_point_id=event.knowledge_point_id,
                    score=Decimal(str(evaluation.score)),
                    evidence_count=evaluation.evidence_count,
                    revision=evaluation.revision,
                )
                session.add(mastery_row)
            else:
                mastery_row.score = Decimal(str(evaluation.score))
                mastery_row.evidence_count = evaluation.evidence_count
                mastery_row.revision = evaluation.revision
            session.flush()

            audit = MasteryUpdateAuditRow(
                event_id=event.event_id,
                student_id=event.student_id,
                course_id=event.course_id,
                knowledge_point_id=event.knowledge_point_id,
                previous_score=Decimal(str(previous_score)) if previous_score is not None else None,
                new_score=Decimal(str(evaluation.score)),
                previous_evidence_count=current.evidence_count,
                new_evidence_count=evaluation.evidence_count,
                revision=evaluation.revision,
                evidence_value=Decimal(str(evaluation.evidence_value)),
                evidence_weight=Decimal(str(evaluation.evidence_weight)),
                policy_version=evaluation.policy_version,
                reason_code=evaluation.reason_code,
            )
            session.add(audit)
            session.flush()
            return self._audit_result(audit, applied=True, duplicate=False)

    def list_mastery_audit(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        limit: int = 100,
    ) -> Sequence[MasteryAuditRecord]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._session_factory() as session:
            rows = session.scalars(
                select(MasteryUpdateAuditRow)
                .where(
                    MasteryUpdateAuditRow.student_id == student_id,
                    MasteryUpdateAuditRow.course_id == course_id,
                )
                .order_by(
                    MasteryUpdateAuditRow.created_at,
                    MasteryUpdateAuditRow.event_id,
                )
                .limit(limit)
            ).all()
            return tuple(self._audit_record(row) for row in rows)

    @staticmethod
    def _event_from_row(row: LearningEventRow) -> LearningEvent:
        return LearningEvent(
            event_id=row.event_id,
            schema_version=row.schema_version,
            event_type=cast(LearningEventType, row.event_type),
            occurred_at=row.occurred_at,
            student_id=row.student_id,
            course_id=cast(CourseId, row.course_id),
            course_version=row.course_version,
            knowledge_point_id=row.knowledge_point_id,
            trace_id=row.trace_id,
            payload=dict(row.payload),
            evidence_summary=row.evidence_summary,
        )

    @staticmethod
    def _validate_decision(
        event: LearningEvent,
        current: MasterySnapshot,
        decision: MasteryDecision,
    ) -> None:
        if decision.knowledge_point_id != event.knowledge_point_id:
            raise ValueError("policy cannot redirect evidence to another knowledge point")
        if not 0 <= decision.score <= 1:
            raise ValueError("policy score must be between 0 and 1")
        if decision.evidence_count != current.evidence_count + 1:
            raise ValueError("policy must increment evidence_count exactly once")
        if decision.revision != current.revision + 1:
            raise ValueError("policy must increment revision exactly once")
        if not 0 <= decision.evidence_value <= 1:
            raise ValueError("policy evidence_value must be between 0 and 1")
        if not 0 < decision.evidence_weight <= 1:
            raise ValueError("policy evidence_weight must be in (0, 1]")

    @staticmethod
    def _audit_result(
        row: MasteryUpdateAuditRow,
        *,
        applied: bool,
        duplicate: bool,
    ) -> MasteryUpdateResult:
        return MasteryUpdateResult(
            event_id=row.event_id,
            applied=applied,
            duplicate=duplicate,
            reason_code=cast(MasteryReasonCode, row.reason_code),
            knowledge_point_id=row.knowledge_point_id,
            previous_score=float(row.previous_score) if row.previous_score is not None else None,
            new_score=float(row.new_score),
            previous_evidence_count=row.previous_evidence_count,
            new_evidence_count=row.new_evidence_count,
            revision=row.revision,
            policy_version=row.policy_version,
        )

    @staticmethod
    def _audit_record(row: MasteryUpdateAuditRow) -> MasteryAuditRecord:
        return MasteryAuditRecord(
            event_id=row.event_id,
            student_id=row.student_id,
            course_id=cast(CourseId, row.course_id),
            knowledge_point_id=row.knowledge_point_id,
            previous_score=float(row.previous_score) if row.previous_score is not None else None,
            new_score=float(row.new_score),
            previous_evidence_count=row.previous_evidence_count,
            new_evidence_count=row.new_evidence_count,
            revision=row.revision,
            evidence_value=float(row.evidence_value),
            evidence_weight=float(row.evidence_weight),
            policy_version=row.policy_version,
            reason_code=cast(MasteryReasonCode, row.reason_code),
            created_at=row.created_at,
        )

    @staticmethod
    def _validate_student_id(student_id: str) -> None:
        if not student_id.strip() or len(student_id) > 128:
            raise ValueError("student_id must be a non-empty internal identifier")
