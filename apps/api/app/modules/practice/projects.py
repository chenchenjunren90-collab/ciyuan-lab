"""Project artifact intake with transparent, non-scoring evidence checks."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.modules.course_content import CourseId, CoursePackRepository
from app.modules.learner_profile.models import MasteryState
from app.modules.learner_profile.records import LearningEvent
from app.modules.learning_flow.service import LearningStore


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectSubmissionRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    artifact_summary: str = Field(min_length=30, max_length=4_000)
    repository_url: str | None = Field(default=None, max_length=1_000)
    test_evidence: list[str] = Field(default_factory=list, max_length=20)


class EvidenceCheck(StrictModel):
    item: str
    present: bool
    detail: str


class ProjectSubmissionResponse(StrictModel):
    submission_id: str
    project_id: str
    status: Literal["evidence_recorded"]
    feedback: str
    evidence_checklist: list[EvidenceCheck]
    mastery_unchanged: list[MasteryState]


class ProjectSubmissionService:
    """Record project evidence without inventing a human or automatic score."""

    def __init__(self, *, courses: CoursePackRepository, repository: LearningStore) -> None:
        self._courses = courses
        self._repository = repository

    def submit(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        project_id: str,
        artifact_summary: str,
        repository_url: str | None,
        test_evidence: list[str],
    ) -> ProjectSubmissionResponse:
        profile = self._repository.get_profile(student_id=student_id, course_id=course_id)
        if profile is None:
            raise LookupError("learner profile not found; complete assessment first")
        project = self._courses.get_activity(course_id, project_id)
        if project.type != "project":
            raise ValueError("activity is not a project")
        if repository_url and not repository_url.startswith(("https://", "http://")):
            raise ValueError("repository_url must use http or https")
        clean_evidence = [item.strip() for item in test_evidence if item.strip()]
        submission_id = uuid4()
        metadata = self._courses.get_version_metadata(course_id)
        summary_hash = hashlib.sha256(artifact_summary.strip().encode("utf-8")).hexdigest()
        event = LearningEvent(
            event_id=uuid4(),
            schema_version="0.1.0",
            event_type="practice.submitted",
            occurred_at=datetime.now(UTC),
            student_id=student_id,
            course_id=course_id,
            course_version=metadata.version,
            knowledge_point_id=project.concept_ids[0] if project.concept_ids else None,
            trace_id=str(submission_id),
            payload={
                "project_id": project_id,
                "project_status": "evidence_recorded_not_scored",
                "automatic_score_applied": False,
                "artifact_summary_hash": summary_hash,
                "artifact_summary_length": len(artifact_summary.strip()),
                "repository_url_present": bool(repository_url),
                "test_evidence_count": len(clean_evidence),
            },
            evidence_summary="综合项目材料与自测证据已记录，未自动评分",
        )
        self._repository.append_event(event)
        checks = [
            EvidenceCheck(
                item="项目说明",
                present=True,
                detail="已收到实现说明；系统仅保存摘要哈希和长度用于审计。",
            ),
            EvidenceCheck(
                item="可复核代码位置",
                present=bool(repository_url),
                detail="已提供仓库链接。" if repository_url else "建议补充仓库或制品链接。",
            ),
            EvidenceCheck(
                item="测试证据",
                present=bool(clean_evidence),
                detail=(
                    f"已列出 {len(clean_evidence)} 条测试证据。"
                    if clean_evidence
                    else "请补充正常、边界和错误路径的测试记录。"
                ),
            ),
        ]
        return ProjectSubmissionResponse(
            submission_id=str(submission_id),
            project_id=project_id,
            status="evidence_recorded",
            feedback=(
                "系统已记录项目说明与自测证据，并完成材料完整性检查；"
                "综合项目不自动评分，也不会据此改变掌握度。"
            ),
            evidence_checklist=checks,
            mastery_unchanged=profile.mastery,
        )
