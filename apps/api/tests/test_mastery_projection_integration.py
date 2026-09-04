"""Real PostgreSQL acceptance tests for DATA-02 transaction guarantees."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import create_database_engine, create_session_factory
from app.modules.learner_profile import (
    CourseVersion,
    LearnerProfileService,
    LearningEvent,
    LearningRepository,
)

_DATABASE_URL = os.getenv("CIYUAN_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL,
    reason="CIYUAN_TEST_DATABASE_URL is required for real PostgreSQL acceptance",
)


def _alembic_config() -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = _DATABASE_URL
    return config


def test_event_projection_is_atomic_idempotent_audited_and_reversible() -> None:
    assert _DATABASE_URL is not None
    config = _alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_database_engine(_DATABASE_URL)
    repository = LearningRepository(create_session_factory(engine))
    service = LearnerProfileService(repository)
    student_id = str(uuid4())
    first_event_id = uuid4()
    second_event_id = uuid4()
    rejected_event_id = uuid4()
    concurrent_event_ids = (uuid4(), uuid4())
    try:
        course_version = CourseVersion(
            course_id="python",
            version="0.1.0",
            title="Python程序设计",
            status="draft",
            manifest_hash="a" * 64,
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            tuple(
                executor.map(
                    lambda _: repository.register_course_version(course_version),
                    range(2),
                )
            )
        active_course = repository.get_active_course_version("python")
        assert active_course == course_version
        with ThreadPoolExecutor(max_workers=2) as executor:
            tuple(
                executor.map(
                    lambda _: repository.create_profile(
                        student_id=student_id,
                        course_id="python",
                        course_version="0.1.0",
                    ),
                    range(2),
                )
            )
        first = LearningEvent(
            event_id=first_event_id,
            schema_version="0.1.0",
            event_type="assessment.completed",
            occurred_at=datetime.now(UTC),
            student_id=student_id,
            course_id="python",
            course_version="0.1.0",
            knowledge_point_id="PY-BASE-01",
            payload={"is_correct": True},
            evidence_summary="synthetic assessment result",
        )
        assert repository.append_event(first) is True

        applied = service.process_event(first_event_id)
        duplicate = service.process_event(first_event_id)
        assert applied.applied is True
        assert applied.duplicate is False
        assert applied.previous_score is None
        assert applied.new_score == 0.725
        assert applied.new_evidence_count == 1
        assert applied.revision == 1
        assert duplicate.applied is False
        assert duplicate.duplicate is True
        assert duplicate.new_score == applied.new_score

        second = LearningEvent(
            event_id=second_event_id,
            schema_version="0.1.0",
            event_type="code.verified",
            occurred_at=datetime.now(UTC),
            student_id=student_id,
            course_id="python",
            course_version="0.1.0",
            knowledge_point_id="PY-BASE-01",
            payload={"accepted": False, "passed_tests": 1, "total_tests": 2},
        )
        assert repository.append_event(second) is True
        second_result = service.process_event(second_event_id)
        assert second_result.new_score == 0.6463
        assert second_result.new_evidence_count == 2
        assert second_result.revision == 2

        rejected = LearningEvent(
            event_id=rejected_event_id,
            schema_version="0.1.0",
            event_type="practice.submitted",
            occurred_at=datetime.now(UTC),
            student_id=student_id,
            course_id="python",
            course_version="0.1.0",
            knowledge_point_id="PY-FLOW-01",
            payload={"feedback": "no objective result"},
        )
        assert repository.append_event(rejected) is True
        rejected_result = service.process_event(rejected_event_id)
        assert rejected_result.applied is False
        assert rejected_result.reason_code == "insufficient_evidence"

        profile = repository.get_profile(student_id=student_id, course_id="python")
        assert profile is not None
        profile_states = [
            (item.knowledge_point_id, item.score, item.evidence_count)
            for item in profile.mastery
        ]
        assert profile_states == [("PY-BASE-01", 0.6463, 2)]
        audit = repository.list_mastery_audit(student_id=student_id, course_id="python")
        assert [item.event_id for item in audit] == [first_event_id, second_event_id]
        assert audit[0].policy_version == "evidence-ewma-v1"
        assert audit[1].previous_score == 0.725

        for concurrent_event_id, is_correct in zip(
            concurrent_event_ids,
            (True, False),
            strict=True,
        ):
            assert repository.append_event(
                LearningEvent(
                    event_id=concurrent_event_id,
                    schema_version="0.1.0",
                    event_type="assessment.completed",
                    occurred_at=datetime.now(UTC),
                    student_id=student_id,
                    course_id="python",
                    course_version="0.1.0",
                    knowledge_point_id="PY-CONCURRENCY-01",
                    payload={"is_correct": is_correct},
                )
            )
        with ThreadPoolExecutor(max_workers=2) as executor:
            concurrent_results = tuple(executor.map(service.process_event, concurrent_event_ids))
        assert all(item.applied for item in concurrent_results)

        concurrent_profile = repository.get_profile(
            student_id=student_id,
            course_id="python",
        )
        assert concurrent_profile is not None
        concurrent_state = next(
            item
            for item in concurrent_profile.mastery
            if item.knowledge_point_id == "PY-CONCURRENCY-01"
        )
        assert concurrent_state.evidence_count == 2
        assert concurrent_state.score in {0.3988, 0.6013}
    finally:
        engine.dispose()

    command.downgrade(config, "20260822_0001")
    engine = create_database_engine(_DATABASE_URL)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "mastery_update_audits" not in tables
        assert "mastery_states" in tables
    finally:
        engine.dispose()
    command.upgrade(config, "head")
