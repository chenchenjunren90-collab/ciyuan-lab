"""Relational persistence models for course versions and learning evidence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_COURSE_ID_CHECK = "course_id IN ('c', 'python', 'data_structures')"
_EVENT_TYPE_CHECK = (
    "event_type IN ('assessment.completed', 'practice.submitted', "
    "'code.verified', 'profile.updated', 'recommendation.generated')"
)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class CourseVersionRow(Base):
    __tablename__ = "course_versions"
    __table_args__ = (
        CheckConstraint(_COURSE_ID_CHECK, name="course_id_allowed"),
        Index(
            "uq_course_versions_one_active",
            "course_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    course_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32))
    manifest_hash: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearnerProfileRow(Base):
    __tablename__ = "learner_profiles"
    __table_args__ = (
        CheckConstraint(_COURSE_ID_CHECK, name="course_id_allowed"),
        ForeignKeyConstraint(
            ["course_id", "course_version"],
            ["course_versions.course_id", "course_versions.version"],
            ondelete="RESTRICT",
        ),
    )

    student_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    course_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MasteryStateRow(Base):
    __tablename__ = "mastery_states"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
        CheckConstraint("evidence_count >= 0", name="evidence_count_nonnegative"),
        CheckConstraint("revision >= 1", name="revision_positive"),
        ForeignKeyConstraint(
            ["student_id", "course_id"],
            ["learner_profiles.student_id", "learner_profiles.course_id"],
            ondelete="CASCADE",
        ),
        Index("ix_mastery_states_course_knowledge", "course_id", "knowledge_point_id"),
    )

    student_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    knowledge_point_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearningEventRow(Base):
    __tablename__ = "learning_events"
    __table_args__ = (
        CheckConstraint(_COURSE_ID_CHECK, name="course_id_allowed"),
        CheckConstraint(_EVENT_TYPE_CHECK, name="event_type_allowed"),
        ForeignKeyConstraint(
            ["student_id", "course_id"],
            ["learner_profiles.student_id", "learner_profiles.course_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_id", "course_version"],
            ["course_versions.course_id", "course_versions.version"],
            ondelete="RESTRICT",
        ),
        Index("ix_learning_events_student_course_time", "student_id", "course_id", "occurred_at"),
        Index("ix_learning_events_trace_id", "trace_id"),
    )

    event_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(16))
    event_type: Mapped[str] = mapped_column(String(48))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    student_id: Mapped[str] = mapped_column(String(128))
    course_id: Mapped[str] = mapped_column(String(32))
    course_version: Mapped[str] = mapped_column(String(32))
    knowledge_point_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class MasteryUpdateAuditRow(Base):
    """One immutable audit record for each event applied to mastery."""

    __tablename__ = "mastery_update_audits"
    __table_args__ = (
        CheckConstraint("new_score >= 0 AND new_score <= 1", name="new_score_range"),
        CheckConstraint(
            "previous_score IS NULL OR (previous_score >= 0 AND previous_score <= 1)",
            name="previous_score_range",
        ),
        CheckConstraint(
            "evidence_value >= 0 AND evidence_value <= 1",
            name="evidence_value_range",
        ),
        CheckConstraint(
            "evidence_weight > 0 AND evidence_weight <= 1",
            name="evidence_weight_range",
        ),
        CheckConstraint(
            "previous_evidence_count >= 0 AND new_evidence_count = previous_evidence_count + 1",
            name="evidence_count_step",
        ),
        CheckConstraint("revision >= 1", name="revision_positive"),
        ForeignKeyConstraint(
            ["event_id"],
            ["learning_events.event_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["student_id", "course_id", "knowledge_point_id"],
            [
                "mastery_states.student_id",
                "mastery_states.course_id",
                "mastery_states.knowledge_point_id",
            ],
            ondelete="RESTRICT",
        ),
        Index(
            "ix_mastery_audits_student_course_time",
            "student_id",
            "course_id",
            "created_at",
        ),
    )

    event_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(128))
    course_id: Mapped[str] = mapped_column(String(32))
    knowledge_point_id: Mapped[str] = mapped_column(String(80))
    previous_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    new_score: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    previous_evidence_count: Mapped[int] = mapped_column(Integer)
    new_evidence_count: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer)
    evidence_value: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    evidence_weight: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    policy_version: Mapped[str] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
