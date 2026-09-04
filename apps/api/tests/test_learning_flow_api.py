"""The baseline assessment produces evidence, a plan and a next activity."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_diagnostic_service, get_learning_flow_service
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
from app.modules.learning_flow.diagnostics import DiagnosticService
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
    app.dependency_overrides[get_diagnostic_service] = lambda: DiagnosticService(
        courses=CoursePackRepository(), learning_flow=service
    )
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


def test_two_learners_keep_independent_profiles(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, store = client_and_store
    for student_id, is_correct in (("learner-alpha", True), ("learner-beta", False)):
        response = client.post(
            "/api/v1/assessments",
            json={
                "student_id": student_id,
                "course_id": "python",
                "answers": [
                    {"knowledge_point_id": "PY-BASE-01", "is_correct": is_correct}
                ],
            },
        )
        assert response.status_code == 200

    alpha = client.get(
        "/api/v1/profile",
        params={"student_id": "learner-alpha", "course_id": "python"},
    ).json()
    beta = client.get(
        "/api/v1/profile",
        params={"student_id": "learner-beta", "course_id": "python"},
    ).json()

    assert alpha["student_id"] == "learner-alpha"
    assert beta["student_id"] == "learner-beta"
    assert alpha["mastery"][0]["score"] == 0.725
    assert beta["mastery"][0]["score"] == 0.275
    assert set(store.profiles) >= {
        ("learner-alpha", "python"),
        ("learner-beta", "python"),
    }


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


def test_diagnostic_hides_answers_and_server_grades_submission(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, store = client_and_store
    quiz_response = client.get(
        "/api/v1/diagnostics",
        params={"course_id": "python", "phase": "initial"},
    )

    assert quiz_response.status_code == 200
    quiz = quiz_response.json()
    assert quiz["phase"] == "initial"
    assert len(quiz["items"]) == 12
    assert all("accepted_answers" not in item for item in quiz["items"])
    assert all(item["skill_atoms"] for item in quiz["items"])
    assert all(
        item["options"][-1] == {
            "id": "UNKNOWN",
            "text": "我不知道 / 还没有学过",
        }
        for item in quiz["items"]
    )
    correct_positions: list[int] = []
    repository = CoursePackRepository()
    for item in quiz["items"]:
        record = repository.get_practice_activity("python", item["exercise_id"])
        accepted_source_ids = set(record.evaluation["accepted_answers"])
        accepted_texts = {
            option["text"]
            for option in record.evaluation["options"]
            if option["id"] in accepted_source_ids
        }
        correct_positions.append(next(
            index for index, option in enumerate(item["options"][:-1])
            if option["text"] in accepted_texts
        ))
    assert set(correct_positions) == {0, 1, 2, 3}
    assert max(correct_positions.count(position) for position in range(4)) <= 3
    answers = [
        {"exercise_id": item["exercise_id"], "response": item["options"][0]["id"]}
        for item in quiz["items"]
    ]

    result = client.post(
        "/api/v1/diagnostics/submissions",
        json={
            "student_id": "diagnostic-student",
            "course_id": "python",
            "phase": "initial",
            "answers": answers,
        },
    )

    assert result.status_code == 200
    payload = result.json()
    assert payload["total_count"] == 12
    assert payload["correct_count"] == sum(
        item["correct"] for item in payload["item_results"]
    )
    assert payload["unknown_count"] == 0
    assert all(item["unknown"] is False for item in payload["item_results"])
    assert len(store.events) == 12
    assert payload["profile"]["mastery"]
    assert payload["analysis"]["course_core_nodes"] == 40
    assert payload["analysis"]["course_skill_atoms"] == 158
    assert payload["analysis"]["assessed_skill_atoms"] > 0
    assert payload["analysis"]["evidence_scope"] == "knowledge_point_proxy"


def test_diagnostic_unknown_answers_are_not_counted_as_mastery(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, store = client_and_store
    quiz = client.get(
        "/api/v1/diagnostics",
        params={"course_id": "python", "phase": "initial"},
    ).json()

    result = client.post(
        "/api/v1/diagnostics/submissions",
        json={
            "student_id": "zero-basis-student",
            "course_id": "python",
            "phase": "initial",
            "answers": [
                {"exercise_id": item["exercise_id"], "response": "UNKNOWN"}
                for item in quiz["items"]
            ],
        },
    )

    assert result.status_code == 200
    payload = result.json()
    assert payload["correct_count"] == 0
    assert payload["unknown_count"] == payload["total_count"] == 12
    assert all(item["unknown"] is True for item in payload["item_results"])
    assert all(item["correct"] is False for item in payload["item_results"])
    assert len(store.events) == 12


def test_diagnostic_rejects_missing_or_invented_items(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, _ = client_and_store

    response = client.post(
        "/api/v1/diagnostics/submissions",
        json={
            "student_id": "diagnostic-student",
            "course_id": "python",
            "phase": "reassessment",
            "answers": [{"exercise_id": "PY-NOT-REAL", "response": "A"}],
        },
    )

    assert response.status_code == 422
    assert "must match the current quiz" in response.json()["detail"]


def test_diagnostic_detects_later_skill_with_missing_prerequisite(
    client_and_store: tuple[TestClient, MemoryLearningStore],
) -> None:
    client, _ = client_and_store
    repository = CoursePackRepository()
    quiz = client.get(
        "/api/v1/diagnostics",
        params={"course_id": "python", "phase": "initial"},
    ).json()
    answers = []
    for item in quiz["items"]:
        record = repository.get_practice_activity("python", item["exercise_id"])
        accepted_source_ids = set(record.evaluation["accepted_answers"])
        accepted_texts = {
            option["text"]
            for option in record.evaluation["options"]
            if option["id"] in accepted_source_ids
        }
        accepted = {
            option["id"] for option in item["options"]
            if option["text"] in accepted_texts
        }
        response = next(iter(accepted))
        if item["exercise_id"] == "PY-BASE-02-Q1":
            response = next(
                option["id"] for option in item["options"] if option["id"] not in accepted
            )
        answers.append({"exercise_id": item["exercise_id"], "response": response})

    result = client.post(
        "/api/v1/diagnostics/submissions",
        json={
            "student_id": "non-linear-student",
            "course_id": "python",
            "phase": "initial",
            "answers": answers,
        },
    )

    assert result.status_code == 200
    analysis = result.json()["analysis"]
    assert analysis["non_linear_profile"] is True
    assert any(
        gap["missing_prerequisite_id"] == "PY-BASE-02"
        and gap["downstream_id"] in {"PY-BASE-03", "PY-BASE-04", "PY-LIST-01"}
        for gap in analysis["prerequisite_gaps"]
    )
    assert analysis["focus_knowledge_point_ids"][0] == "PY-BASE-02"
    assert analysis["learning_blocks"][0]["skill_atoms"]
