"""Python immersive lessons are scripted, grounded and safe to expose."""

import asyncio
from typing import Any, cast

from fastapi.testclient import TestClient

from app.main import app
from app.modules.course_content import CoursePackRepository
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.orchestration.classroom import ClassroomLessonService
from app.modules.orchestration.ports import PlannedActivity

client = TestClient(app)


class _AdaptiveLearningContext:
    def __init__(self, profile: LearnerProfile, planned: PlannedActivity) -> None:
        self.profile = profile
        self.planned = planned

    def get_profile(self, *, student_id: str, course_id: str) -> LearnerProfile:
        assert student_id == self.profile.student_id
        assert course_id == "python"
        return self.profile

    async def next_activity(self, *, student_id: str, course_id: str) -> PlannedActivity:
        assert student_id == self.profile.student_id
        assert course_id == "python"
        return self.planned


def test_first_python_lesson_exposes_complete_flow_without_hidden_tests() -> None:
    response = client.get("/api/v1/classroom/lessons/python-list-filter-01")

    assert response.status_code == 200
    payload = cast(dict[str, Any], response.json())
    assert payload["course_id"] == "python"
    assert [beat["phase"] for beat in payload["beats"]] == [
        "welcome",
        "concept",
        "discussion",
        "debug",
        "practice",
        "summary",
        "homework",
    ]
    assert len(payload["cast"]) == 5
    assert payload["practice"]["exercise_id"] == "PY-LIST-03-C1"
    assert payload["homework"]["exercise_id"] == "PY-LIST-03-H1"
    assert len(payload["practice"]["public_examples"]) == 2
    assert len(payload["homework"]["public_examples"]) == 2
    assert payload["practice"]["input_format"]
    assert payload["practice"]["output_format"]
    assert payload["practice"]["constraints"]
    assert all(item["explanation"] for item in payload["practice"]["public_examples"])
    assert all(beat["board_explanation"] for beat in payload["beats"])
    assert all(beat["board_trace"] for beat in payload["beats"])
    assert "hidden" not in response.text.casefold()


def test_checkpoint_waits_for_understanding_and_allows_retry() -> None:
    wrong = client.post(
        "/api/v1/classroom/checkpoints",
        json={
            "lesson_id": "python-list-filter-01",
            "beat_id": "beat-filter",
            "response": "A",
        },
    )
    correct = client.post(
        "/api/v1/classroom/checkpoints",
        json={
            "lesson_id": "python-list-filter-01",
            "beat_id": "beat-filter",
            "response": "B",
        },
    )

    assert wrong.status_code == 200
    assert wrong.json()["accepted"] is False
    assert correct.status_code == 200
    assert correct.json()["accepted"] is True
    assert correct.json()["reply_role"] == "teacher"


def test_second_python_lesson_is_real_and_uses_dictionary_tasks() -> None:
    response = client.get("/api/v1/classroom/lessons/python-dict-lookup-02")

    assert response.status_code == 200
    payload = cast(dict[str, Any], response.json())
    assert payload["title"] == "字典与快速查找"
    assert payload["knowledge_point_ids"] == ["PY-DICT-01", "PY-DICT-02"]
    assert payload["practice"]["exercise_id"] == "PY-DICT-02-C1"
    assert payload["homework"]["exercise_id"] == "PY-DICT-01-H1"
    assert len(payload["practice"]["public_examples"]) == 2
    assert payload["homework"]["public_examples"]
    assert all(beat["board_explanation"] for beat in payload["beats"])

    checkpoint = client.post(
        "/api/v1/classroom/checkpoints",
        json={
            "lesson_id": "python-dict-lookup-02",
            "beat_id": "dict-beat-lookup",
            "response": "C",
        },
    )
    assert checkpoint.status_code == 200
    assert checkpoint.json()["accepted"] is True


def test_adaptive_session_repairs_prerequisite_gap_and_uses_real_code_tasks() -> None:
    profile = LearnerProfile(
        student_id="non-linear-student",
        course_id="python",
        mastery=[
            MasteryState(knowledge_point_id="PY-LIST-03", score=0.9, evidence_count=2),
        ],
    )
    service = ClassroomLessonService(
        CoursePackRepository(),
        learning_context=_AdaptiveLearningContext(
            profile,
            PlannedActivity(
                activity_id="PY-DICT-02-C1",
                activity_type="code",
                reason="优先修复已经证实的前置断层",
            ),
        ),
    )

    lesson = asyncio.run(
        service.next_session(
            student_id=profile.student_id,
            daily_minutes=45,
            preferred_mode="step_by_step",
        )
    )

    assert lesson.delivery_mode == "adaptive"
    assert len(lesson.knowledge_point_ids) == 2
    assert lesson.knowledge_point_ids != ["PY-DICT-01", "PY-DICT-02"]
    assert lesson.practice.exercise_id != lesson.homework.exercise_id
    assert lesson.practice.public_examples
    assert lesson.homework.public_examples
    assert {"practice", "homework"}.issubset({beat.action for beat in lesson.beats})
    instructional_beats = [
        beat for beat in lesson.beats
        if beat.id.startswith(("adaptive-concept--", "adaptive-checkpoint--", "adaptive-example--"))
    ]
    assert len(instructional_beats) == len(lesson.knowledge_point_ids) * 2
    assert all(beat.board_explanation for beat in instructional_beats)
    assert all(beat.board_trace for beat in instructional_beats)
    assert any(
        point.startswith("易错提醒：")
        for beat in instructional_beats
        for point in beat.board_points
    )
    assert "优先修复" in lesson.planning_reason

    restored = service.get_lesson(lesson.lesson_id)
    assert restored.knowledge_point_ids == lesson.knowledge_point_ids


def test_zero_basis_self_report_overrides_guessed_diagnostic_mastery() -> None:
    profile = LearnerProfile(
        student_id="guessed-but-zero-basis",
        course_id="python",
        mastery=[
            MasteryState(knowledge_point_id="PY-LIST-03", score=0.95, evidence_count=1),
            MasteryState(knowledge_point_id="PY-DICT-02", score=0.9, evidence_count=1),
        ],
    )
    service = ClassroomLessonService(
        CoursePackRepository(),
        learning_context=_AdaptiveLearningContext(
            profile,
            PlannedActivity(
                activity_id="PY-DATA-02-Q1",
                activity_type="objective",
                reason="短测分数较高",
            ),
        ),
    )

    lesson = asyncio.run(service.next_session(
        student_id=profile.student_id,
        daily_minutes=45,
        preferred_mode="step_by_step",
        self_profile_level="newcomer",
    ))

    assert lesson.knowledge_point_ids == ["PY-BASE-01", "PY-BASE-02"]
    assert "零基础" in lesson.planning_reason
    assert "不会因猜对而跳级" in lesson.planning_reason


def test_adaptive_session_scales_content_with_daily_budget() -> None:
    profile = LearnerProfile(
        student_id="tier-student",
        course_id="python",
        mastery=[
            MasteryState(knowledge_point_id="PY-BASE-01", score=0.8, evidence_count=2),
            MasteryState(knowledge_point_id="PY-BASE-02", score=0.8, evidence_count=2),
        ],
    )
    service = ClassroomLessonService(
        CoursePackRepository(),
        learning_context=_AdaptiveLearningContext(
            profile,
            PlannedActivity(
                activity_id="PY-BASE-03-Q1",
                activity_type="objective",
                reason="按薄弱点继续推进",
            ),
        ),
    )

    light = asyncio.run(service.next_session(
        student_id=profile.student_id,
        daily_minutes=20,
        preferred_mode="step_by_step",
    ))
    assert len(light.knowledge_point_ids) == 1
    assert len(light.beats) == 6
    assert "轻量课堂" in light.subtitle

    standard = asyncio.run(service.next_session(
        student_id=profile.student_id,
        daily_minutes=45,
        preferred_mode="step_by_step",
    ))
    assert len(standard.knowledge_point_ids) == 2
    assert len(standard.beats) == 8
    assert "标准课堂" in standard.subtitle

    deep = asyncio.run(service.next_session(
        student_id=profile.student_id,
        daily_minutes=120,
        preferred_mode="step_by_step",
    ))
    assert len(deep.knowledge_point_ids) == 3
    assert len(deep.beats) == 10
    assert "深度课堂" in deep.subtitle


def test_classroom_dialogue_uses_persona_and_traceable_python_evidence() -> None:
    response = client.post(
        "/api/v1/classroom/dialogue",
        json={
            "student_id": "classroom-test",
            "lesson_id": "python-list-filter-01",
            "phase": "discussion",
            "role": "peer_cautious",
            "message": "for 和 if 分别负责什么？",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["role"] == "peer_cautious"
    assert payload["display_name"] == "小禾"
    assert payload["citations"]
    assert all(item["source_id"].startswith("SRC-PY-") for item in payload["citations"])
    assert [item["component"] for item in payload["trace"]] == [
        "retrieval",
        "course_tutor",
        "quality_supervisor",
    ]


def test_unknown_classroom_lesson_is_not_silently_substituted() -> None:
    response = client.get("/api/v1/classroom/lessons/not-a-lesson")

    assert response.status_code == 404


def test_self_report_is_conservatively_matched_to_course_route() -> None:
    response = client.post(
        "/api/v1/classroom/self-profile",
        json={
            "student_id": "self-profile-test",
            "lesson_id": "python-list-filter-01",
            "description": (
                "我学过变量、if、for、列表和函数，做过课程作业，但调试时经常不知道从哪里开始。"
            ),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["level"] in {"developing", "experienced"}
    assert payload["recommended_start"]
    assert payload["matched_knowledge_point_ids"]
    assert payload["signals"]
    assert "短测" in payload["advisor_message"] or "摸底" in payload["advisor_message"]
    assert [item["component"] for item in payload["trace"]] == [
        "retrieval",
        "course_tutor",
        "quality_supervisor",
    ]
