"""Evidence-driven assessment, profile and planning application service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID, uuid4

from app.modules.course_content.models import CourseId
from app.modules.course_content.repository import CoursePackRepository
from app.modules.learner_profile.models import LearnerProfile
from app.modules.learner_profile.policy import EvidenceMasteryPolicy, MasteryPolicy
from app.modules.learner_profile.records import (
    CourseVersion,
    LearningEvent,
    MasteryUpdateResult,
    RecommendationCandidate,
)
from app.modules.learner_profile.service import LearnerProfileService
from app.modules.learning_flow.models import AssessmentOutcome, PlanStageRecord
from app.modules.model_adapters.ports import ModelAdapter
from app.modules.orchestration.ports import PlannedActivity
from app.modules.orchestration.service import build_learning_planner


class LearningStore(Protocol):
    def register_course_version(self, course: CourseVersion) -> None: ...

    def create_profile(
        self, *, student_id: str, course_id: CourseId, course_version: str
    ) -> None: ...

    def append_event(self, event: LearningEvent) -> bool: ...

    def project_event(self, *, event_id: UUID, policy: MasteryPolicy) -> MasteryUpdateResult: ...

    def get_profile(self, *, student_id: str, course_id: CourseId) -> LearnerProfile | None: ...


class LearningFlowService:
    """Runs deterministic evidence updates before asking the planning agent."""

    def __init__(
        self,
        *,
        repository: LearningStore,
        courses: CoursePackRepository,
        model_adapter: ModelAdapter,
        policy: MasteryPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._courses = courses
        self._model_adapter = model_adapter
        self._policy = policy or EvidenceMasteryPolicy()

    async def submit_assessment(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        answers: Sequence[tuple[str, bool]],
        evidence_source: str = "legacy_client_assessment",
    ) -> AssessmentOutcome:
        self._validate_student_id(student_id)
        knowledge_points = self._courses.list_knowledge_points(course_id)
        known_ids = {item.id for item in knowledge_points}
        answer_ids = [knowledge_point_id for knowledge_point_id, _ in answers]
        if not answer_ids:
            raise ValueError("assessment answers must not be empty")
        if len(answer_ids) != len(set(answer_ids)):
            raise ValueError("assessment knowledge_point_id values must be unique")
        if any(type(is_correct) is not bool for _, is_correct in answers):
            raise ValueError("assessment outcomes must be boolean")
        unknown = sorted(set(answer_ids) - known_ids)
        if unknown:
            raise ValueError(f"assessment contains unknown knowledge points: {unknown}")

        metadata = self._courses.get_version_metadata(course_id)
        self._repository.register_course_version(
            CourseVersion(
                course_id=course_id,
                version=metadata.version,
                title=metadata.title,
                status=metadata.status,
                manifest_hash=metadata.manifest_hash,
            )
        )
        self._repository.create_profile(
            student_id=student_id,
            course_id=course_id,
            course_version=metadata.version,
        )

        assessment_id = uuid4()
        occurred_at = datetime.now(UTC)
        objective_evidence = evidence_source in {"diagnostic_initial", "diagnostic_reassessment"}
        for knowledge_point_id, is_correct in answers:
            event = LearningEvent(
                event_id=uuid4(),
                schema_version="0.1.0",
                event_type="assessment.completed",
                occurred_at=occurred_at,
                student_id=student_id,
                course_id=course_id,
                course_version=metadata.version,
                knowledge_point_id=knowledge_point_id,
                trace_id=str(assessment_id),
                payload={
                    "is_correct" if objective_evidence else "self_reported_correct": is_correct,
                    "source": evidence_source,
                    "objective_evidence": objective_evidence,
                },
                evidence_summary=(
                    "服务端能力诊断结果" if objective_evidence else "学习者自述，未客观计分"
                ),
            )
            if self._repository.append_event(event) and objective_evidence:
                self._repository.project_event(event_id=event.event_id, policy=self._policy)

        profile = self._require_profile(student_id=student_id, course_id=course_id)
        next_activity = await self._next_activity(student_id=student_id, course_id=course_id)
        if not objective_evidence:
            next_activity = PlannedActivity(
                activity_id=next_activity.activity_id,
                activity_type=next_activity.activity_type,
                reason=(
                    "已记录自述，未计入客观学习证据或更新掌握度；请完成服务端能力诊断。"
                    + next_activity.reason
                ),
            )
        stages = self._build_stages(
            profile=profile,
            course_id=course_id,
            next_activity=next_activity,
            knowledge_point_ids=[item.id for item in knowledge_points],
        )
        return AssessmentOutcome(
            profile=profile,
            stages=stages,
            next_activity=next_activity,
        )

    def get_profile(self, *, student_id: str, course_id: CourseId) -> LearnerProfile:
        self._validate_student_id(student_id)
        return self._require_profile(student_id=student_id, course_id=course_id)

    async def next_activity(self, *, student_id: str, course_id: CourseId) -> PlannedActivity:
        self._validate_student_id(student_id)
        self._require_profile(student_id=student_id, course_id=course_id)
        return await self._next_activity(student_id=student_id, course_id=course_id)

    async def _next_activity(self, *, student_id: str, course_id: CourseId) -> PlannedActivity:
        planner = build_learning_planner(
            course_id=course_id,
            profile_provider=lambda student_id, requested_course_id: self._repository.get_profile(
                student_id=student_id,
                course_id=cast(CourseId, requested_course_id),
            ),
            model_adapter=self._model_adapter,
            top_k=12,
        )
        return await planner.next_activity(student_id, course_id)

    def _require_profile(self, *, student_id: str, course_id: CourseId) -> LearnerProfile:
        profile = self._repository.get_profile(student_id=student_id, course_id=course_id)
        if profile is None:
            raise LookupError("learner profile not found")
        return profile

    @staticmethod
    def _validate_student_id(student_id: str) -> None:
        if not student_id.strip() or len(student_id) > 128:
            raise ValueError("student_id must be between 1 and 128 characters")

    @staticmethod
    def _build_stages(
        *,
        profile: LearnerProfile,
        course_id: CourseId,
        next_activity: PlannedActivity,
        knowledge_point_ids: Sequence[str],
    ) -> tuple[PlanStageRecord, ...]:
        top_k = min(12, len(knowledge_point_ids))
        candidates = LearnerProfileService.build_recommendation_data(
            profile=profile,
            course_knowledge_point_ids=knowledge_point_ids,
            top_k=top_k,
        )
        candidates_by_id = {candidate.knowledge_point_id: candidate for candidate in candidates}
        ordered_ids = list(candidates_by_id)
        if next_activity.activity_type == "concept" and next_activity.activity_id in ordered_ids:
            ordered_ids.remove(next_activity.activity_id)
            ordered_ids.insert(0, next_activity.activity_id)

        stage_names = (
            ("阶段一：当前重点", "补齐薄弱知识并建立可靠学习证据"),
            ("阶段二：核心进阶", "在前置知识基础上完成核心练习"),
            ("阶段三：综合应用", "综合运用所学知识解决完整问题"),
        )
        stages: list[PlanStageRecord] = []
        for index, (stage, objective) in enumerate(stage_names):
            stage_ids = tuple(ordered_ids[index * 4 : (index + 1) * 4])
            if not stage_ids:
                continue
            stage_candidates = tuple(
                candidates_by_id[knowledge_point_id] for knowledge_point_id in stage_ids
            )
            reason = LearningFlowService._stage_reason(stage_candidates, course_id)
            stages.append(
                PlanStageRecord(
                    stage=stage,
                    objective=objective,
                    knowledge_point_ids=stage_ids,
                    reason=reason,
                )
            )
        return tuple(stages)

    @staticmethod
    def _stage_reason(candidates: Sequence[RecommendationCandidate], course_id: CourseId) -> str:
        counts: dict[str, int] = {}
        for candidate in candidates:
            counts[candidate.reason_code] = counts.get(candidate.reason_code, 0) + 1
        return (
            f"依据 {course_id} 课程画像排序："
            f"待巩固 {counts.get('needs_reinforcement', 0)} 项，"
            f"证据不足 {counts.get('insufficient_evidence', 0)} 项，"
            f"继续练习 {counts.get('continue_practice', 0)} 项"
        )
