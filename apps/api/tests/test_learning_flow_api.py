"""The baseline assessment produces evidence, a plan and a next activity."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_learning_flow_service
from app.main import app
from app.modules.course_content import CoursePackRepository
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
from app.modules.learning_flow import LearningFlowService
from app.modules.model_adapters import MockAdapter


class MemoryLearningStore:
    def __init__(self) -> None:
        self.profiles: dict[tuple[str, str], LearnerProfile] = {}
        self.events: dict[UUID, LearningEvent] = {}
        self.versions: list[CourseVersion] = []

    def register_course_version(self, course: CourseVersion) -> None:
        self.versions.append(course)

    def create_profile(
        self, *, student_id: str, course_id: CourseId, course_version: str
    ) -> None:
        self.profiles.setdefault(
            (student_id, course_id),
            LearnerProfile(student_id=student_id, course_id=course_id),
        )

    def append_event(self, event: LearningEvent) -> bool:
        if event.event_id in self.events:
            return False
        self.events[event.event_id] = event
        return True

    def project_event(
        self, *, event_id: UUID, policy: MasteryPolicy
    ) -> MasteryUpdateResult:
        event = self.events[event_id]
        profile = self.profiles[(event.student_id, event.course_id)]
        existing = next(
            (
                state
                for state in profile.mastery
                if state.knowledge_point_id == event.knowledge_point_id
            ),
            None,
        )
        current = MasterySnapshot(
            score=existing.score if existing else policy.initial_score,
            evidence_count=existing.evidence_count if existing else 0,
            revision=existing.evidence_count if existing else 0,
        )
        decision = policy.evaluate(event, current)
        assert isinstance(decision, MasteryDecision)
        assert event.knowledge_point_id is not None
        profile.mastery = [
            state
            for state in profile.mastery
            if state.knowledge_point_id != event.knowledge_point_id
        ]
        profile.mastery.append(
            MasteryState(
                knowledge_point_id=event.knowledge_point_id,
                score=decision.score,
                evidence_count=decision.evidence_count,
                updated_at=datetime.now(UTC),
            )
        )
        return MasteryUpdateResult(
            event_id=event.event_id,
            applied=True,
            duplicate=False,
            reason_code=decision.reason_code,
            knowledge_point_id=event.knowledge_point_id,
            new_score=decision.score,
            new_evidence_count=decision.evidence_count,
            revision=decision.revision,
            policy_version=decision.policy_version,
        )

    def get_profile(
        self, *, student_id: str, course_id: CourseId
    ) -> LearnerProfile | None:
        return self.profiles.get((student_id, course_id))


@pytest.fixture
def client_and_store() -> Generator[tuple[TestClient, MemoryLearningStore]]:
    store = MemoryLearningStore()
    service = LearningFlowService(
        repository=store,
        courses=CoursePackRepository(),
        model_adapter=MockAdapter(),
    )
    app.dependency_overrides[get_learning_flow_service] = lambda: service
    try:
        yield TestClient(app), store
    finally:
        app.dependency_overrides.clear()


def test_assessment_updates_profile_and_returns_plan(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, store = client_and_store

    response = client.post(
        "/api/v1/assessments",
        json={
            "student_id": "demo-student-1",
            "course_id": "python",
            "answers": [
                {"knowledge_point_id": "PY-BASE-01", "is_correct": True},
                {"knowledge_point_id": "PY-BASE-02", "is_correct": False},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    scores = {
        item["knowledge_point_id"]: item["score"]
        for item in payload["profile"]["mastery"]
    }
    assert scores == {"PY-BASE-01": 0.725, "PY-BASE-02": 0.275}
    assert payload["plan"]["stages"]
    assert payload["plan"]["next_activity"]["activity_id"]
    assert len(store.events) == 2
    assert store.versions[-1].course_id == "python"


def test_profile_and_next_activity_are_available_after_assessment(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, _ = client_and_store
    request = {
        "student_id": "demo-student-2",
        "course_id": "python",
        "answers": [{"knowledge_point_id": "PY-BASE-01", "is_correct": True}],
    }
    assert client.post("/api/v1/assessments", json=request).status_code == 200

    profile = client.get(
        "/api/v1/profile",
        params={"student_id": "demo-student-2", "course_id": "python"},
    )
    next_activity = client.get(
        "/api/v1/next-activity",
        params={"student_id": "demo-student-2", "course_id": "python"},
    )

    assert profile.status_code == 200
    assert profile.json()["mastery"][0]["evidence_count"] == 1
    assert next_activity.status_code == 200
    assert next_activity.json()["activity_id"]


def test_assessment_rejects_unknown_knowledge_point(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, _ = client_and_store

    response = client.post(
        "/api/v1/assessments",
        json={
            "student_id": "demo-student-3",
            "course_id": "python",
            "answers": [{"knowledge_point_id": "PY-NOT-REAL", "is_correct": True}],
        },
    )

    assert response.status_code == 422
    assert "unknown knowledge points" in response.json()["detail"]


def test_profile_returns_not_found_before_assessment(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, _ = client_and_store

    response = client.get(
        "/api/v1/profile",
        params={"student_id": "missing", "course_id": "python"},
    )

    assert response.status_code == 404
