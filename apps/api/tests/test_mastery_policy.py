"""Fast unit tests for the DATA-02 policy and recommendation boundary."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.policy import EvidenceMasteryPolicy
from app.modules.learner_profile.records import (
    LearningEvent,
    MasteryDecision,
    MasteryRejection,
    MasterySnapshot,
)
from app.modules.learner_profile.service import LearnerProfileService


def _event(
    event_type: str,
    payload: dict[str, object],
    *,
    knowledge_point_id: str | None = "PY-BASE-01",
) -> LearningEvent:
    return LearningEvent(
        event_id=uuid4(),
        schema_version="0.1.0",
        event_type=event_type,  # type: ignore[arg-type]
        occurred_at=datetime.now(UTC),
        student_id="00000000-0000-4000-8000-000000000001",
        course_id="python",
        course_version="0.1.0",
        knowledge_point_id=knowledge_point_id,
        payload=payload,
    )


def test_assessment_policy_is_deterministic_and_versioned() -> None:
    policy = EvidenceMasteryPolicy()
    result = policy.evaluate(
        _event("assessment.completed", {"is_correct": True}),
        MasterySnapshot(score=0.5, evidence_count=0, revision=0),
    )

    assert isinstance(result, MasteryDecision)
    assert result.score == 0.725
    assert result.evidence_count == 1
    assert result.revision == 1
    assert result.reason_code == "assessment_result"
    assert result.policy_version == "evidence-ewma-v1"


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        ("assessment.completed", {"is_correct": "yes"}),
        ("practice.submitted", {}),
        ("code.verified", {"passed_tests": 3, "total_tests": 2}),
        (
            "code.verified",
            {"passed_tests": 2, "total_tests": 2, "accepted": False},
        ),
    ],
)
def test_malformed_or_conflicting_payload_never_updates(
    event_type: str,
    payload: dict[str, object],
) -> None:
    result = EvidenceMasteryPolicy().evaluate(
        _event(event_type, payload),
        MasterySnapshot(score=0.5, evidence_count=0, revision=0),
    )
    assert result == MasteryRejection(reason_code="insufficient_evidence")


def test_non_evidence_event_and_missing_knowledge_point_never_update() -> None:
    policy = EvidenceMasteryPolicy()
    state = MasterySnapshot(score=0.5, evidence_count=0, revision=0)

    unsupported = policy.evaluate(_event("profile.updated", {}), state)
    missing_target = policy.evaluate(
        _event("assessment.completed", {"is_correct": True}, knowledge_point_id=None),
        state,
    )

    assert unsupported == MasteryRejection(reason_code="unsupported_event")
    assert missing_target == MasteryRejection(reason_code="insufficient_evidence")


def test_code_verification_uses_objective_test_ratio() -> None:
    result = EvidenceMasteryPolicy().evaluate(
        _event(
            "code.verified",
            {"accepted": False, "passed_tests": 3, "total_tests": 4},
        ),
        MasterySnapshot(score=0.5, evidence_count=2, revision=2),
    )

    assert isinstance(result, MasteryDecision)
    assert result.score == 0.5875
    assert result.evidence_value == 0.75
    assert result.reason_code == "code_test_ratio"


def test_recommendation_data_is_explainable_stable_and_course_bounded() -> None:
    profile = LearnerProfile(
        student_id="00000000-0000-4000-8000-000000000001",
        course_id="python",
        mastery=[
            MasteryState(
                knowledge_point_id="PY-BASE-01",
                score=0.4,
                evidence_count=3,
            ),
            MasteryState(
                knowledge_point_id="PY-FUNC-01",
                score=0.85,
                evidence_count=4,
            ),
        ],
    )

    result = LearnerProfileService.build_recommendation_data(
        profile=profile,
        course_knowledge_point_ids=["PY-BASE-01", "PY-FLOW-01", "PY-FUNC-01"],
        top_k=3,
    )

    assert [item.knowledge_point_id for item in result] == [
        "PY-BASE-01",
        "PY-FLOW-01",
        "PY-FUNC-01",
    ]
    assert [item.reason_code for item in result] == [
        "needs_reinforcement",
        "insufficient_evidence",
        "ready_to_progress",
    ]
    assert result[0].confidence == 0.6


def test_recommendation_rejects_unknown_profile_knowledge_point() -> None:
    profile = LearnerProfile(
        student_id="00000000-0000-4000-8000-000000000001",
        course_id="python",
        mastery=[MasteryState(knowledge_point_id="PY-UNKNOWN", score=0.5)],
    )

    with pytest.raises(ValueError, match="unknown knowledge points"):
        LearnerProfileService.build_recommendation_data(
            profile=profile,
            course_knowledge_point_ids=["PY-BASE-01"],
        )
