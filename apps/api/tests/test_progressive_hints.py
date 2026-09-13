from typing import Literal

from app.modules.course_content import CoursePackRepository
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.practice.hints import ProgressiveHintService


class ProfileStore:
    def get_profile(self, *, student_id: str, course_id: str) -> LearnerProfile:
        return LearnerProfile(
            student_id=student_id,
            course_id=course_id,
            mastery=[MasteryState(knowledge_point_id="PY-ALGO-01", score=0.2, evidence_count=1)],
        )


def test_progressive_hints_are_distinct_and_never_claim_to_reveal_answer() -> None:
    courses = CoursePackRepository()
    activity = next(
        item
        for item in courses.list_activities("python")
        if item.type in {"objective", "code", "debug"}
    )
    service = ProgressiveHintService(
        courses=courses,
        repository=ProfileStore(),  # type: ignore[arg-type]
    )

    levels: tuple[Literal[1, 2, 3], ...] = (1, 2, 3)
    hints = [
        service.create_hint(
            student_id="hint-student",
            course_id="python",
            activity_id=activity.id,
            level=level,
        )
        for level in levels
    ]

    assert len({item.hint for item in hints}) == 3
    assert all(not item.answer_revealed for item in hints)
    assert all(item.source_refs for item in hints)


def test_project_hint_keeps_focus_on_computer_science_workflow() -> None:
    courses = CoursePackRepository()
    project = next(item for item in courses.list_activities("python") if item.type == "project")
    service = ProgressiveHintService(
        courses=courses,
        repository=ProfileStore(),  # type: ignore[arg-type]
    )

    result = service.create_hint(
        student_id="hint-student",
        course_id="python",
        activity_id=project.id,
        level=3,
    )

    assert "输入校验" in result.hint
    assert "测试证据" in result.hint


def test_ta_hint_uses_public_output_difference_instead_of_generic_course_copy() -> None:
    service = ProgressiveHintService(
        courses=CoursePackRepository(),
        repository=ProfileStore(),  # type: ignore[arg-type]
    )

    result = service.create_hint(
        student_id="hint-student",
        course_id="python",
        activity_id="PY-BASE-01-H1",
        level=1,
        source_code='name = input()\nprint(f"你好， {name}！")',
        diagnostics=["公开测试 public-normal 未通过：期望 '你好，小词！'，实际 '你好， 小词！'"],
        passed_tests=0,
        total_tests=2,
    )

    assert "0/2" in result.hint
    assert "逗号后多了一个空格" in result.hint
    assert "CPython" not in result.hint
    assert not result.answer_revealed


def test_ta_hint_hands_off_hidden_boundary_without_revealing_hidden_case() -> None:
    service = ProgressiveHintService(
        courses=CoursePackRepository(),
        repository=ProfileStore(),  # type: ignore[arg-type]
    )

    result = service.create_hint(
        student_id="hint-student",
        course_id="python",
        activity_id="PY-BASE-01-H1",
        level=1,
        source_code='name = input()\nprint(f"你好，{name}！")',
        diagnostics=["隐藏测试未通过（输入与期望输出已隐藏）"],
        passed_tests=1,
        total_tests=2,
    )

    assert "1/2" in result.hint
    assert "首尾空格" in result.hint
    assert "隐藏" in result.hint
    assert "小元" not in result.hint
