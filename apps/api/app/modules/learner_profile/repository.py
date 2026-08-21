"""Synchronous repository with explicit transactions for learning evidence."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.modules.learner_profile.db_models import (
    CourseVersionRow,
    LearnerProfileRow,
    LearningEventRow,
    MasteryStateRow,
)
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.records import (
    CourseId,
    CourseVersion,
    LearningEvent,
    LearningEventType,
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

            row = session.get(CourseVersionRow, (course.course_id, course.version))
            if row is None:
                row = CourseVersionRow(
                    course_id=course.course_id,
                    version=course.version,
                    title=course.title,
                    status=course.status,
                    manifest_hash=course.manifest_hash,
                    is_active=course.is_active,
                )
                session.add(row)
            else:
                row.title = course.title
                row.status = course.status
                row.manifest_hash = course.manifest_hash
                row.is_active = course.is_active

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
            row = session.get(LearnerProfileRow, (student_id, course_id))
            if row is None:
                session.add(
                    LearnerProfileRow(
                        student_id=student_id,
                        course_id=course_id,
                        course_version=course_version,
                    )
                )
            elif row.course_version != course_version:
                row.course_version = course_version

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

    @staticmethod
    def _validate_student_id(student_id: str) -> None:
        if not student_id.strip() or len(student_id) > 128:
            raise ValueError("student_id must be a non-empty internal identifier")
