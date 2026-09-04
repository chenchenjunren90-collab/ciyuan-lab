"""Submissions produce objective evidence and a verified next step."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.modules.course_content import CourseId, CoursePackRepository
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.policy import MasteryPolicy
from app.modules.learner_profile.records import (
    CourseVersion,
    LearningEvent,
    MasteryUpdateResult,
)
from app.modules.orchestration.ports import PlannedActivity
from app.modules.practice.ports import (
    CodeTestCase,
    SupportedLanguage,
    VerificationResult,
)
from app.modules.practice.service import PracticeSubmissionService


class MemoryStore:
    def __init__(self, profile: LearnerProfile) -> None:
        self.profile = profile
        self.events: list[LearningEvent] = []

    def register_course_version(self, course: CourseVersion) -> None:
        del course

    def create_profile(
        self, *, student_id: str, course_id: CourseId, course_version: str
    ) -> None:
        del student_id, course_id, course_version

    def append_event(self, event: LearningEvent) -> bool:
        self.events.append(event)
        return True

    def project_event(
        self, *, event_id: UUID, policy: MasteryPolicy
    ) -> MasteryUpdateResult:
        del policy
        event = next(item for item in self.events if item.event_id == event_id)
        assert event.knowledge_point_id is not None
        accepted = event.payload["accepted"] is True
        self.profile.mastery = [
            state
            for state in self.profile.mastery
            if state.knowledge_point_id != event.knowledge_point_id
        ]
        self.profile.mastery.append(
            MasteryState(
                knowledge_point_id=event.knowledge_point_id,
                score=0.75 if accepted else 0.25,
                evidence_count=1,
                updated_at=datetime.now(UTC),
            )
        )
        return MasteryUpdateResult(
            event_id=event_id,
            applied=True,
            duplicate=False,
            reason_code=(
                "practice_result"
                if event.event_type == "practice.submitted"
                else "code_test_ratio"
            ),
            knowledge_point_id=event.knowledge_point_id,
            new_score=0.75 if accepted else 0.25,
            new_evidence_count=1,
        )

    def get_profile(
        self, *, student_id: str, course_id: CourseId
    ) -> LearnerProfile | None:
        if self.profile.student_id == student_id and self.profile.course_id == course_id:
            return self.profile
        return None


class AcceptedVerifier:
    async def verify(
        self,
        language: SupportedLanguage,
        source_code: str,
        tests: Sequence[CodeTestCase],
        limits: Mapping[str, int],
    ) -> VerificationResult:
        del language, source_code, limits
        return VerificationResult(
            accepted=True,
            passed_tests=len(tests),
            total_tests=len(tests),
            diagnostics=(),
        )


class FixedNextActivity:
    async def next_activity(
        self, *, student_id: str, course_id: CourseId
    ) -> PlannedActivity:
        del student_id, course_id
        return PlannedActivity(
            activity_id="PY-DATA-02",
            activity_type="concept",
            reason="继续数据处理学习",
        )


def build_service(profile: LearnerProfile) -> tuple[PracticeSubmissionService, MemoryStore]:
    store = MemoryStore(profile)
    service = PracticeSubmissionService(
        repository=store,
        courses=CoursePackRepository(),
        verifier=AcceptedVerifier(),
        learning_flow=FixedNextActivity(),
    )
    return service, store


def test_objective_submission_updates_mastery() -> None:
    service, store = build_service(LearnerProfile(student_id="s1", course_id="c"))

    result = asyncio.run(
        service.submit(
            student_id="s1",
            course_id="c",
            exercise_id="C-BASE-01-Q1",
            response="A",
            language=None,
            source_code=None,
        )
    )

    assert result.verification is None
    assert result.profile.mastery[0].score == 0.75
    assert store.events[0].event_type == "practice.submitted"


def test_code_submission_uses_all_hidden_tests_without_leaking_them() -> None:
    service, store = build_service(
        LearnerProfile(student_id="s2", course_id="python")
    )

    result = asyncio.run(
        service.submit(
            student_id="s2",
            course_id="python",
            exercise_id="PY-DATA-01-C1",
            response=None,
            language="python",
            source_code="print('verified by fake sandbox')",
        )
    )

    assert result.verification is not None
    assert result.verification.accepted is True
    assert result.verification.total_tests >= 2
    assert result.verification.diagnostics == []
    assert store.events[0].event_type == "code.verified"


def test_submission_requires_existing_profile() -> None:
    service, _ = build_service(LearnerProfile(student_id="other", course_id="c"))

    try:
        asyncio.run(
            service.submit(
                student_id="missing",
                course_id="c",
                exercise_id="C-BASE-01-Q1",
                response="A",
                language=None,
                source_code=None,
            )
        )
    except LookupError as exc:
        assert "complete assessment first" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing profile must be rejected")
