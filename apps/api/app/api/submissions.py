"""Deterministic exercise submission endpoint."""

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_practice_submission_service
from app.api.schemas import NextActivity
from app.modules.course_content import CourseId, CourseRecordNotFoundError
from app.modules.practice import (
    PracticeSubmissionService,
    SubmissionRequest,
    SubmissionResult,
)

router = APIRouter(tags=["practice"])
CourseIdQuery = Annotated[CourseId, Query()]


@router.post("/exercises/{exercise_id}/submissions", response_model=SubmissionResult)
async def submit_exercise(
    exercise_id: str,
    request: SubmissionRequest,
    service: Annotated[PracticeSubmissionService, Depends(get_practice_submission_service)],
    course_id: CourseIdQuery,
) -> SubmissionResult:
    try:
        result = await service.submit(
            student_id=request.student_id,
            course_id=course_id,
            exercise_id=exercise_id,
            response=request.response,
            language=request.language,
            source_code=request.source_code,
        )
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail="exercise not found") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SubmissionResult(
        verification=result.verification,
        feedback=result.feedback,
        citations=[],
        mastery_updated=result.profile.mastery,
        next_activity=NextActivity(
            activity_id=result.next_activity.activity_id,
            activity_type=cast(Any, result.next_activity.activity_type),
            reason=result.next_activity.reason,
        ),
    )
