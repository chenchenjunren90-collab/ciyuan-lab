"""Deterministic adaptive problem generation and mastery evidence tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_adaptive_problem_service
from app.main import app
from app.modules.adaptive_practice import AdaptiveProblemService
from app.modules.course_content.models import CourseId
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.policy import MasteryPolicy
from app.modules.learner_profile.records import (
    CourseVersion,
    LearningEvent,
    MasteryDecision,
    MasterySnapshot,
    MasteryUpdateResult,
)
from app.modules.practice.ports import CodeTestCase, VerificationResult


class MemoryStore:
    def __init__(self) -> None:
        self.profile = LearnerProfile(
            student_id="adaptive-student",
            course_id="python",
            mastery=[
                MasteryState(
                    knowledge_point_id="PY-DICT-01",
                    score=0.2,
                    evidence_count=1,
                )
            ],
        )
        self.events: dict[UUID, LearningEvent] = {}

    def register_course_version(self, course: CourseVersion) -> None:
        del course

    def create_profile(
        self, *, student_id: str, course_id: CourseId, course_version: str
    ) -> None:
        del student_id, course_id, course_version

    def append_event(self, event: LearningEvent) -> bool:
        self.events[event.event_id] = event
        return True

    def project_event(
        self, *, event_id: UUID, policy: MasteryPolicy
    ) -> MasteryUpdateResult:
        event = self.events[event_id]
        current_state = next(
            item
            for item in self.profile.mastery
            if item.knowledge_point_id == event.knowledge_point_id
        )
        decision = policy.evaluate(
            event,
            MasterySnapshot(
                score=current_state.score,
                evidence_count=current_state.evidence_count,
                revision=current_state.evidence_count,
            ),
        )
        assert isinstance(decision, MasteryDecision)
        self.profile.mastery = [
            item
            for item in self.profile.mastery
            if item.knowledge_point_id != event.knowledge_point_id
        ]
        self.profile.mastery.append(
            MasteryState(
                knowledge_point_id=decision.knowledge_point_id,
                score=decision.score,
                evidence_count=decision.evidence_count,
                updated_at=datetime.now(UTC),
            )
        )
        return MasteryUpdateResult(
            event_id=event_id,
            applied=True,
            duplicate=False,
            reason_code=decision.reason_code,
            knowledge_point_id=decision.knowledge_point_id,
            new_score=decision.score,
            new_evidence_count=decision.evidence_count,
        )

    def get_profile(
        self, *, student_id: str, course_id: CourseId
    ) -> LearnerProfile | None:
        if student_id == self.profile.student_id and course_id == self.profile.course_id:
            return self.profile
        return None


class AcceptingVerifier:
    def __init__(self) -> None:
        self.cases: tuple[CodeTestCase, ...] = ()

    async def verify(
        self,
        language: Literal["c", "python"],
        source_code: str,
        tests: Sequence[CodeTestCase],
        limits: Mapping[str, int],
    ) -> VerificationResult:
        assert language == "python"
        assert source_code.strip()
        assert limits["time_limit_ms"] == 2000
        self.cases = tuple(tests)
        return VerificationResult(
            accepted=True,
            passed_tests=len(tests),
            total_tests=len(tests),
            diagnostics=(),
        )


@pytest.fixture
def adaptive_client() -> Generator[TestClient]:
    service = AdaptiveProblemService(
        repository=MemoryStore(), verifier=AcceptingVerifier()
    )
    app.dependency_overrides[get_adaptive_problem_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_generated_problem_targets_weak_skill_and_hides_tests() -> None:
    store = MemoryStore()
    verifier = AcceptingVerifier()
    service = AdaptiveProblemService(repository=store, verifier=verifier)

    first = service.generate(
        student_id="adaptive-student", course_id="python", attempt_index=1
    )
    repeated = service.generate(
        student_id="adaptive-student", course_id="python", attempt_index=1
    )

    assert first == repeated
    assert first.concept_ids == ["PY-DICT-01"]
    assert first.problem_id.startswith("GEN-PY-DICT-COUNT-1-")
    assert len(first.public_examples) == 1
    assert "hidden" not in first.model_dump_json().lower()


def test_submission_updates_profile_and_returns_new_variant() -> None:
    store = MemoryStore()
    verifier = AcceptingVerifier()
    service = AdaptiveProblemService(repository=store, verifier=verifier)
    problem = service.generate(
        student_id="adaptive-student", course_id="python", attempt_index=1
    )

    result = asyncio.run(
        service.submit(
            student_id="adaptive-student",
            problem_id=problem.problem_id,
            source_code="print('demo')",
        )
    )

    assert result.verification.accepted is True
    assert len(verifier.cases) == 3
    assert any(case.visibility == "hidden" for case in verifier.cases)
    state = next(
        item
        for item in result.profile.mastery
        if item.knowledge_point_id == "PY-DICT-01"
    )
    assert state.evidence_count == 2
    assert result.next_problem.problem_id != problem.problem_id


def test_problem_id_is_bound_to_student() -> None:
    service = AdaptiveProblemService(repository=MemoryStore(), verifier=AcceptingVerifier())
    problem = service.generate(
        student_id="adaptive-student", course_id="python", attempt_index=1
    )

    with pytest.raises(ValueError, match="does not belong"):
        service._parse_problem_id("another-student", problem.problem_id)


def test_adaptive_http_flow_does_not_expose_hidden_tests(
    adaptive_client: TestClient,
) -> None:
    generated = adaptive_client.post(
        "/api/v1/adaptive-problems/generate",
        json={
            "student_id": "adaptive-student",
            "course_id": "python",
            "attempt_index": 1,
        },
    )
    assert generated.status_code == 200
    problem = generated.json()
    assert "hidden" not in generated.text.lower()

    submitted = adaptive_client.post(
        f"/api/v1/adaptive-problems/{problem['problem_id']}/submissions",
        json={"student_id": "adaptive-student", "source_code": "print('demo')"},
    )
    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["verification"]["accepted"] is True
    assert payload["next_problem"]["problem_id"] != problem["problem_id"]
    assert "hidden" not in submitted.text.lower()
