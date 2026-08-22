"""Real PostgreSQL acceptance test for DATA-01."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import create_database_engine, create_session_factory
from app.modules.learner_profile import CourseVersion, LearningEvent, LearningRepository

_DATABASE_URL = os.getenv("CIYUAN_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL,
    reason="CIYUAN_TEST_DATABASE_URL is required for real PostgreSQL acceptance",
)


def _alembic_config() -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = _DATABASE_URL
    return config


def test_migrations_queries_idempotency_and_rollback() -> None:
    assert _DATABASE_URL is not None
    config = _alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_database_engine(_DATABASE_URL)
    repository = LearningRepository(create_session_factory(engine))
    student_id = str(uuid4())
    event_id = uuid4()
    try:
        assert {
            "course_versions",
            "learner_profiles",
            "mastery_states",
            "learning_events",
        }.issubset(set(inspect(engine).get_table_names()))

        repository.register_course_version(
            CourseVersion(
                course_id="python",
                version="0.1.0",
                title="Python程序设计",
                status="draft",
                manifest_hash="a" * 64,
            )
        )
        repository.register_course_version(
            CourseVersion(
                course_id="python",
                version="0.2.0",
                title="Python程序设计",
                status="draft",
                manifest_hash="b" * 64,
            )
        )
        active_course = repository.get_active_course_version("python")
        assert active_course is not None
        assert active_course.version == "0.2.0"
        repository.create_profile(
            student_id=student_id,
            course_id="python",
            course_version="0.2.0",
        )
        repository.store_mastery_snapshot(
            student_id=student_id,
            course_id="python",
            knowledge_point_id="PY-BASE-01",
            score=0.75,
            evidence_count=2,
            revision=1,
        )
        event = LearningEvent(
            event_id=event_id,
            schema_version="0.1.0",
            event_type="assessment.completed",
            occurred_at=datetime.now(UTC),
            student_id=student_id,
            course_id="python",
            course_version="0.2.0",
            knowledge_point_id="PY-BASE-01",
            trace_id="test-trace",
            payload={"is_correct": True},
            evidence_summary="synthetic test evidence",
        )
        assert repository.append_event(event) is True
        assert repository.append_event(event) is False

        profile = repository.get_profile(student_id=student_id, course_id="python")
        assert profile is not None
        assert profile.student_id == student_id
        assert profile.mastery[0].knowledge_point_id == "PY-BASE-01"
        assert profile.mastery[0].score == 0.75
        stored_events = repository.list_events(student_id=student_id, course_id="python")
        assert [stored.event_id for stored in stored_events] == [event_id]
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_database_engine(_DATABASE_URL)
    try:
        remaining_tables = set(inspect(engine).get_table_names())
        assert not {
            "course_versions",
            "learner_profiles",
            "mastery_states",
            "learning_events",
        } & remaining_tables
    finally:
        engine.dispose()
    command.upgrade(config, "head")
