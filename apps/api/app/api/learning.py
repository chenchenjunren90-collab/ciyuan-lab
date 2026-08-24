"""Assessment, profile and next-activity endpoints for the learning loop."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.dependencies import get_learning_flow_service
from app.api.schemas import NextActivity
from app.modules.course_content.models import CourseId
from app.modules.learner_profile.models import LearnerProfile
from app.modules.learning_flow import LearningFlowService

router = APIRouter(tags=["learning"])
LearningFlowDependency = Annotated[LearningFlowService, Depends(get_learning_flow_service)]
StudentIdQuery = Annotated[str, Query(min_length=1, max_length=128)]
CourseIdQuery = Annotated[CourseId, Query()]


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
