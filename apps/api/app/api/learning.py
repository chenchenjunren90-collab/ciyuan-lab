"""Assessment, profile and next-activity endpoints for the learning loop."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.dependencies import get_diagnostic_service, get_learning_flow_service
from app.api.schemas import NextActivity
from app.modules.course_content.models import CourseId
from app.modules.learner_profile.models import LearnerProfile
from app.modules.learning_flow import LearningFlowService
from app.modules.learning_flow.diagnostics import (
    DiagnosticAnalysis,
    DiagnosticPhase,
    DiagnosticQuiz,
    DiagnosticService,
)

router = APIRouter(tags=["learning"])
LearningFlowDependency = Annotated[LearningFlowService, Depends(get_learning_flow_service)]
StudentIdQuery = Annotated[str, Query(min_length=1, max_length=128)]
CourseIdQuery = Annotated[CourseId, Query()]
DiagnosticServiceDependency = Annotated[DiagnosticService, Depends(get_diagnostic_service)]
DiagnosticPhaseQuery = Annotated[DiagnosticPhase, Query()]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssessmentAnswer(StrictModel):
    knowledge_point_id: str = Field(min_length=1)
    is_correct: bool


class AssessmentRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    course_id: CourseId
    answers: list[AssessmentAnswer] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_knowledge_points(self) -> AssessmentRequest:
        ids = [item.knowledge_point_id for item in self.answers]
        if len(ids) != len(set(ids)):
            raise ValueError("assessment knowledge_point_id values must be unique")
        return self


class PlanStage(StrictModel):
    stage: str
    objective: str
    knowledge_point_ids: list[str]
    reason: str


class Plan(StrictModel):
    student_id: str
    course_id: CourseId
    stages: list[PlanStage]
    next_activity: NextActivity


class AssessmentResult(StrictModel):
    profile: LearnerProfile
    plan: Plan


class DiagnosticAnswer(StrictModel):
    exercise_id: str = Field(min_length=1, max_length=128)
    response: str = Field(min_length=1, max_length=64)


class DiagnosticSubmissionRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    course_id: CourseId
    phase: DiagnosticPhase
    answers: list[DiagnosticAnswer] = Field(min_length=1, max_length=12)


class DiagnosticItemResult(StrictModel):
    exercise_id: str
    knowledge_point_id: str
    correct: bool
    unknown: bool
    skill_atom_ids: list[str]


class DiagnosticSubmissionResult(AssessmentResult):
    phase: DiagnosticPhase
    correct_count: int = Field(ge=0)
    unknown_count: int = Field(ge=0)
    total_count: int = Field(gt=0)
    item_results: list[DiagnosticItemResult]
    analysis: DiagnosticAnalysis


@router.get("/diagnostics", response_model=DiagnosticQuiz)
async def get_diagnostic_quiz(
    service: DiagnosticServiceDependency,
    course_id: CourseIdQuery,
    phase: DiagnosticPhaseQuery = "initial",
) -> DiagnosticQuiz:
    try:
        return service.build_quiz(course_id=course_id, phase=phase)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/diagnostics/submissions", response_model=DiagnosticSubmissionResult)
async def submit_diagnostic(
    request: DiagnosticSubmissionRequest,
    service: DiagnosticServiceDependency,
) -> DiagnosticSubmissionResult:
    try:
        result = await service.submit(
            student_id=request.student_id,
            course_id=request.course_id,
            phase=request.phase,
            answers=[(answer.exercise_id, answer.response) for answer in request.answers],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DiagnosticSubmissionResult(
        phase=result.phase,
        correct_count=sum(item.correct for item in result.grades),
        unknown_count=sum(item.unknown for item in result.grades),
        total_count=len(result.grades),
        item_results=[
            DiagnosticItemResult(
                exercise_id=item.exercise_id,
                knowledge_point_id=item.knowledge_point_id,
                correct=item.correct,
                unknown=item.unknown,
                skill_atom_ids=[atom.id for atom in item.skill_atoms],
            )
            for item in result.grades
        ],
        analysis=result.analysis,
        profile=result.assessment.profile,
        plan=Plan(
            student_id=request.student_id,
            course_id=request.course_id,
            stages=[
                PlanStage(
                    stage=stage.stage,
                    objective=stage.objective,
                    knowledge_point_ids=list(stage.knowledge_point_ids),
                    reason=stage.reason,
                )
                for stage in result.assessment.stages
            ],
            next_activity=NextActivity(
                activity_id=result.assessment.next_activity.activity_id,
                activity_type=cast(Any, result.assessment.next_activity.activity_type),
                reason=result.assessment.next_activity.reason,
            ),
        ),
    )


@router.post("/assessments", response_model=AssessmentResult)
async def submit_assessment(
    request: AssessmentRequest, service: LearningFlowDependency
) -> AssessmentResult:
    try:
        result = await service.submit_assessment(
            student_id=request.student_id,
            course_id=request.course_id,
            answers=[(answer.knowledge_point_id, answer.is_correct) for answer in request.answers],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AssessmentResult(
        profile=result.profile,
        plan=Plan(
            student_id=request.student_id,
            course_id=request.course_id,
            stages=[
                PlanStage(
                    stage=stage.stage,
                    objective=stage.objective,
                    knowledge_point_ids=list(stage.knowledge_point_ids),
                    reason=stage.reason,
                )
                for stage in result.stages
            ],
            next_activity=NextActivity(
                activity_id=result.next_activity.activity_id,
                activity_type=cast(Any, result.next_activity.activity_type),
                reason=result.next_activity.reason,
            ),
        ),
    )


@router.get("/profile", response_model=LearnerProfile)
async def get_profile(
    service: LearningFlowDependency,
    student_id: StudentIdQuery,
    course_id: CourseIdQuery,
) -> LearnerProfile:
    try:
        return service.get_profile(student_id=student_id, course_id=course_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="learner profile not found") from exc


@router.get("/next-activity", response_model=NextActivity)
async def get_next_activity(
    service: LearningFlowDependency,
    student_id: StudentIdQuery,
    course_id: CourseIdQuery,
) -> NextActivity:
    try:
        result = await service.next_activity(student_id=student_id, course_id=course_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="learner profile not found") from exc
    return NextActivity(
        activity_id=result.activity_id,
        activity_type=cast(Any, result.activity_type),
        reason=result.reason,
    )
