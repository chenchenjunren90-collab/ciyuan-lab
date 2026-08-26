from app.modules.course_content import CoursePackRepository
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.records import LearningEvent
from app.modules.practice.projects import ProjectSubmissionService


class EventStore:
    def __init__(self) -> None:
        self.events: list[LearningEvent] = []

    def get_profile(self, *, student_id: str, course_id: str) -> LearnerProfile:
        return LearnerProfile(
            student_id=student_id,
            course_id=course_id,
            mastery=[MasteryState(knowledge_point_id="PY-DATA-01", score=0.6, evidence_count=2)],
        )

    def append_event(self, event: LearningEvent) -> bool:
        self.events.append(event)
        return True


def test_project_submission_records_evidence_without_automatic_score() -> None:
    courses = CoursePackRepository()
    project = next(item for item in courses.list_activities("python") if item.type == "project")
    store = EventStore()
    service = ProjectSubmissionService(
        courses=courses,
        repository=store,  # type: ignore[arg-type]
    )
    summary = "实现了字段解析、数据校验、异常分类和统计汇总，并用正常、边界、错误三类输入完成测试。"

    result = service.submit(
        student_id="project-student",
        course_id="python",
        project_id=project.id,
        artifact_summary=summary,
        repository_url="https://gitee.com/example/project",
        test_evidence=["pytest: 12 passed", "异常输入返回明确错误"],
    )

    assert result.status == "evidence_recorded"
    assert result.mastery_unchanged[0].score == 0.6
    assert all(item.present for item in result.evidence_checklist)
    assert len(store.events) == 1
    payload = store.events[0].payload
    assert payload["project_status"] == "evidence_recorded_not_scored"
    assert payload["automatic_score_applied"] is False
    assert "accepted" not in payload
    assert summary not in str(payload)
