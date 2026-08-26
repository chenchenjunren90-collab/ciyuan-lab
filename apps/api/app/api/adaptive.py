"""Profile-driven generated Python practice endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_adaptive_problem_service
from app.modules.adaptive_practice import AdaptiveProblemService, GeneratedCodeProblem
from app.modules.course_content import CourseId
from app.modules.learner_profile.models import LearnerProfile
from app.modules.practice.models import VerificationResult

router = APIRouter(prefix="/adaptive-problems", tags=["practice"])
AdaptiveServiceDependency = Annotated[AdaptiveProblemService, Depends(get_adaptive_problem_service)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerateProblemRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    course_id: CourseId
    attempt_index: int = Field(default=1, ge=1, le=9999)


class GeneratedProblemSubmissionRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    source_code: str = Field(min_length=1, max_length=100_000)


class GeneratedProblemSubmissionResponse(StrictModel):
    problem: GeneratedCodeProblem
    verification: VerificationResult
    feedback: str
    profile: LearnerProfile
    next_problem: GeneratedCodeProblem


@router.post("/generate", response_model=GeneratedCodeProblem)
async def generate_adaptive_problem(
    request: GenerateProblemRequest,
    service: AdaptiveServiceDependency,
) -> GeneratedCodeProblem:
    try:
        return service.generate(
            student_id=request.student_id,
            course_id=request.course_id,
            attempt_index=request.attempt_index,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{problem_id}/submissions",
    response_model=GeneratedProblemSubmissionResponse,
)
async def submit_adaptive_problem(
    problem_id: str,
    request: GeneratedProblemSubmissionRequest,
    service: AdaptiveServiceDependency,
) -> GeneratedProblemSubmissionResponse:
    try:
        result = await service.submit(
            student_id=request.student_id,
            problem_id=problem_id,
            source_code=request.source_code,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return GeneratedProblemSubmissionResponse(
        problem=result.problem,
        verification=result.verification,
        feedback=result.feedback,
        profile=result.profile,
        next_problem=result.next_problem,
    )
